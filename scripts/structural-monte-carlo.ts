import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type Rng = () => number;

type PathResult = {
  cagr: number;
  maxDrawdown: number;
  finalWealth: number;
  exits: number;
  stopExits: number;
  circuitExits: number;
  marketExits: number;
  monthsInvested: number;
  monthsObserved: number;
  imputedReturnShare: number;
};

const PATHS = Number(process.env.STRUCTURAL_MC_PATHS ?? 2000);
const YEARS = Number(process.env.STRUCTURAL_MC_YEARS ?? 5);
const BLOCK = Number(process.env.STRUCTURAL_MC_BLOCK ?? 20);
const WARMUP = 252;
const HORIZON = YEARS * 252;
const SEED = 20260825;
const cfg = PRODUCTION_STRATEGY;

function mulberry32(seed: number): Rng {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function avg(xs: number[]) { return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0; }
function sdPop(xs: number[]) { const m = avg(xs); return xs.length ? Math.sqrt(avg(xs.map(x => (x - m) ** 2))) : 0; }
function percentile(sorted: number[], p: number) {
  if (!sorted.length) return NaN;
  const x = (sorted.length - 1) * p;
  const lo = Math.floor(x), hi = Math.ceil(x), w = x - lo;
  return sorted[lo] * (1 - w) + sorted[hi] * w;
}
function score(r3: number, r6: number) { return cfg.momentum.threeMonth * r3 + cfg.momentum.sixMonth * r6; }

function latestUniverse(universes: UniverseMonth[], sourceDate: string): UniverseMonth {
  let lo = 0, hi = universes.length - 1, ans = 0;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (universes[mid].asOf <= sourceDate) { ans = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return universes[ans];
}

function buildSignalFast(args: {
  date: string;
  nextSessionDate: string | null;
  universe: UniverseMonth;
  monthly: Map<string, number[]>;
}): MonthlySignal {
  const q = args.monthly.get("QQQ") ?? [];
  const qLast = q.at(-1) ?? null;
  const maWindow = q.slice(-cfg.market.qqqMonthlyMaMonths);
  const qMa = maWindow.length === cfg.market.qqqMonthlyMaMonths ? avg(maWindow) : null;
  const riskOn = qLast !== null && qMa !== null && qLast > qMa;
  const ret = (xs: number[], n: number) => xs.length > n ? xs.at(-1)! / xs.at(-(n + 1))! - 1 : null;
  const q1 = ret(q, 1), q3 = ret(q, 3), q6 = ret(q, 6);
  const qScore = q1 === null || q3 === null || q6 === null ? null : score(q3, q6);
  const candidates: any[] = [];
  for (const member of args.universe.symbols) {
    const xs = args.monthly.get(member.symbol) ?? [];
    const r1 = ret(xs, 1), r3 = ret(xs, 3), r6 = ret(xs, 6);
    if (r1 === null || r3 === null || r6 === null || qScore === null) {
      candidates.push({ symbol: member.symbol, oneMonth: r1, threeMonth: r3, sixMonth: r6, score: null, qqqScore: qScore, scoreSpread: null, eligible: false, exclusionReason: "INSUFFICIENT_PRICE_HISTORY", rank: null });
      continue;
    }
    const s = score(r3, r6);
    const reason = r1 >= cfg.momentum.surgeLimit ? "ONE_MONTH_SURGE" : cfg.momentum.requireAboveQqqScore && s <= qScore ? "NOT_ABOVE_QQQ" : null;
    candidates.push({ symbol: member.symbol, oneMonth: r1, threeMonth: r3, sixMonth: r6, score: s, qqqScore: qScore, scoreSpread: s - qScore, eligible: reason === null, exclusionReason: reason, rank: null });
  }
  const eligible = candidates.filter(x => x.eligible && x.score !== null).sort((a, b) => b.score - a.score || a.symbol.localeCompare(b.symbol));
  eligible.forEach((x, i) => x.rank = i + 1);
  const selected = riskOn ? eligible.slice(0, cfg.selection.topN) : [];
  const valid = selected.length === cfg.selection.topN;
  const dispersion = sdPop(eligible.map(x => x.score));
  const zGap = valid && dispersion > 0 ? (selected[0].score - selected[1].score) / dispersion : valid ? 0 : null;
  const concentrated = zGap !== null && zGap >= cfg.allocation.concentrationZGap;
  const top1 = Math.min(cfg.allocation.maxTop1Weight, concentrated ? cfg.allocation.concentratedTop1Weight : cfg.allocation.baseTop1Weight);
  return {
    strategyId: cfg.strategyId,
    signalMonth: args.date.slice(0, 7),
    signalDate: args.date,
    executionDate: args.nextSessionDate,
    marketRiskOn: riskOn,
    qqqClose: qLast,
    qqqMonthlyMa: qMa,
    qqqScore: qScore,
    universe: args.universe.symbols.map(x => x.symbol),
    candidates: candidates.sort((a, b) => (a.rank ?? 9999) - (b.rank ?? 9999) || (b.score ?? -Infinity) - (a.score ?? -Infinity)),
    selectedSymbols: valid ? selected.map(x => x.symbol) : [],
    targetWeights: valid ? [top1, 1 - top1] : [],
    zGap,
    allocationMode: !valid ? "CASH" : concentrated ? "70/30" : "50/50",
  } as MonthlySignal;
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universeFile = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const universes = [...universeFile.history].sort((a, b) => a.asOf.localeCompare(b.asOf));
  if (!universes.length) throw new Error("Universe history is empty");
  const histories = market.histories;
  const qqq = histories.QQQ;
  if (!qqq?.length) throw new Error("QQQ history missing");
  const sourceDates = qqq.filter(p => p.date >= universes[0].asOf).map(p => p.date);
  if (sourceDates.length < WARMUP + HORIZON) throw new Error(`Need ${WARMUP + HORIZON} source dates; found ${sourceDates.length}`);
  const targetDates = sourceDates.slice(-(WARMUP + HORIZON));
  const symbols = [...new Set(["QQQ", ...universes.flatMap(u => u.symbols.map(x => x.symbol))])];
  const maps = new Map<string, Map<string, PricePoint>>();
  for (const symbol of symbols) maps.set(symbol, new Map((histories[symbol] ?? []).map(p => [p.date, p])));
  const sourceIndex = new Map(sourceDates.map((d, i) => [d, i]));
  const validStarts = sourceDates.map((_, i) => i).filter(i => i >= 1 && i + BLOCK <= sourceDates.length);
  const rng = mulberry32(SEED);
  const results: PathResult[] = [];

  const sourcePath = () => {
    const out: number[] = [];
    while (out.length < targetDates.length) {
      const start = validStarts[Math.floor(rng() * validStarts.length)];
      for (let j = 0; j < BLOCK && out.length < targetDates.length; j++) out.push(start + j);
    }
    return out;
  };

  for (let path = 0; path < PATHS; path++) {
    const sampled = sourcePath();
    const syntheticClose = new Map(symbols.map(s => [s, 100]));
    const monthly = new Map<string, number[]>(symbols.map(s => [s, []]));
    const qqqDaily: PricePoint[] = [];
    let state = initialEngineState(cfg);
    let evalPeak = 1;
    let evalMaxDd = 0;
    let evalStartEquity = 1;
    let evalEndEquity = 1;
    let imputed = 0, factorCount = 0;
    let monthsObserved = 0, monthsInvested = 0;
    const startEventIndex = state.events.length;

    for (let ti = 0; ti < targetDates.length; ti++) {
      const targetDate = targetDates[ti];
      const nextTarget = targetDates[ti + 1] ?? null;
      const si = sampled[ti];
      const srcDate = sourceDates[si];
      const prevSrcDate = sourceDates[si - 1];
      const qCur = maps.get("QQQ")!.get(srcDate)!;
      const qPrev = maps.get("QQQ")!.get(prevSrcDate)!;
      const qOpenFactor = qCur.open / qPrev.close;
      const qCloseFactor = qCur.close / qCur.open;
      const dayPrices: Record<string, PricePoint> = {};

      for (const symbol of symbols) {
        const prevSyn = syntheticClose.get(symbol)!;
        const cur = maps.get(symbol)?.get(srcDate);
        const prev = maps.get(symbol)?.get(prevSrcDate);
        let openFactor = qOpenFactor, closeFactor = qCloseFactor;
        factorCount++;
        if (cur && prev && cur.open > 0 && prev.close > 0) {
          openFactor = cur.open / prev.close;
          closeFactor = cur.close / cur.open;
        } else imputed++;
        const open = Math.max(0.01, prevSyn * openFactor);
        const close = Math.max(0.01, open * closeFactor);
        syntheticClose.set(symbol, close);
        dayPrices[symbol] = { date: targetDate, open, high: Math.max(open, close), low: Math.min(open, close), close } as PricePoint;
      }
      qqqDaily.push(dayPrices.QQQ);

      const monthEnd = nextTarget === null || nextTarget.slice(0, 7) !== targetDate.slice(0, 7);
      let signal: MonthlySignal | null = null;
      if (monthEnd) {
        for (const symbol of symbols) monthly.get(symbol)!.push(syntheticClose.get(symbol)!);
        const mappedUniverse = latestUniverse(universes, srcDate);
        signal = buildSignalFast({ date: targetDate, nextSessionDate: nextTarget, universe: mappedUniverse, monthly });
      }

      if (ti === WARMUP) {
        state = initialEngineState(cfg);
        evalStartEquity = 1;
        evalPeak = 1;
        evalMaxDd = 0;
      }
      if (ti >= WARMUP) {
        const before = state.currentEquity;
        state = transitionDay(state, { date: targetDate, prices: dayPrices, qqqHistoryThroughClose: qqqDaily, monthlySignal: signal, nextSessionDate: nextTarget }, cfg);
        if (ti === WARMUP) evalStartEquity = state.currentEquity || before || 1;
        evalEndEquity = state.currentEquity;
        evalPeak = Math.max(evalPeak, evalEndEquity);
        evalMaxDd = Math.min(evalMaxDd, evalPeak > 0 ? evalEndEquity / evalPeak - 1 : 0);
        if (monthEnd) { monthsObserved++; if (state.currentPositions.length) monthsInvested++; }
      }
    }

    const yearsActual = Math.max(1 / 365.25, (Date.parse(targetDates.at(-1)!) - Date.parse(targetDates[WARMUP])) / (365.25 * 86400000));
    const finalWealth = evalEndEquity / evalStartEquity;
    const cagr = finalWealth ** (1 / yearsActual) - 1;
    const events = state.events.slice(startEventIndex);
    const exits = events.filter(e => e.type === "EXIT_OPEN");
    results.push({
      cagr,
      maxDrawdown: evalMaxDd,
      finalWealth,
      exits: exits.length,
      stopExits: exits.filter(e => e.reason.includes("stop")).length,
      circuitExits: exits.filter(e => e.reason.includes("circuit")).length,
      marketExits: exits.filter(e => e.reason.includes("RiskOff")).length,
      monthsInvested,
      monthsObserved,
      imputedReturnShare: imputed / factorCount,
    });
    if ((path + 1) % 100 === 0) console.log(`completed ${path + 1}/${PATHS}`);
  }

  const cagr = results.map(x => x.cagr).sort((a,b)=>a-b);
  const dd = results.map(x => x.maxDrawdown).sort((a,b)=>a-b);
  const wealth = results.map(x => x.finalWealth).sort((a,b)=>a-b);
  const summary = {
    generatedAt: new Date().toISOString(), strategyId: cfg.strategyId,
    methodology: { paths: PATHS, years: YEARS, blockTradingDays: BLOCK, warmupTradingDays: WARMUP, seed: SEED,
      marketDependence: "Common source-day blocks applied across all symbols and QQQ",
      universeMapping: "At each synthetic month-end, use the latest point-in-time universe available on that sampled source date",
      missingReturnHandling: "When a source symbol lacks OHLC on a sampled source day, use the contemporaneous QQQ open/close factor as a neutral market proxy" },
    distribution: {
      cagr: { p05: percentile(cagr,.05), p25: percentile(cagr,.25), median: percentile(cagr,.5), p75: percentile(cagr,.75), p95: percentile(cagr,.95) },
      maxDrawdown: { adverseP05: percentile(dd,.05), p25: percentile(dd,.25), median: percentile(dd,.5), p75: percentile(dd,.75), p95: percentile(dd,.95) },
      finalWealth: { p05: percentile(wealth,.05), median: percentile(wealth,.5), p95: percentile(wealth,.95) },
      probabilities: {
        cagrGe50: results.filter(x=>x.cagr>=.5).length/PATHS,
        cagrGe80: results.filter(x=>x.cagr>=.8).length/PATHS,
        cagrLt0: results.filter(x=>x.cagr<0).length/PATHS,
        maxDdLe30: results.filter(x=>x.maxDrawdown<=-.3).length/PATHS,
        maxDdLe40: results.filter(x=>x.maxDrawdown<=-.4).length/PATHS,
        maxDdLe50: results.filter(x=>x.maxDrawdown<=-.5).length/PATHS,
        finalWealthLt1: results.filter(x=>x.finalWealth<1).length/PATHS,
      },
      mechanics: {
        medianExits: percentile(results.map(x=>x.exits).sort((a,b)=>a-b),.5),
        medianStopExits: percentile(results.map(x=>x.stopExits).sort((a,b)=>a-b),.5),
        medianCircuitExits: percentile(results.map(x=>x.circuitExits).sort((a,b)=>a-b),.5),
        medianMarketExits: percentile(results.map(x=>x.marketExits).sort((a,b)=>a-b),.5),
        medianInvestedMonthShare: percentile(results.map(x=>x.monthsObserved?x.monthsInvested/x.monthsObserved:0).sort((a,b)=>a-b),.5),
        meanImputedReturnShare: avg(results.map(x=>x.imputedReturnShare)),
      }
    }
  };
  const pct = (x:number) => `${(x*100).toFixed(2)}%`;
  const md = `# Stock-level Structural Monte Carlo\n\nStrategy: **${cfg.strategyId}**  \nPaths: **${PATHS.toLocaleString()}** / Horizon: **${YEARS} years** / Block: **${BLOCK} sessions**\n\n| Metric | Result |\n|---|---:|\n| CAGR p5 | ${pct(summary.distribution.cagr.p05)} |\n| CAGR median | ${pct(summary.distribution.cagr.median)} |\n| CAGR p95 | ${pct(summary.distribution.cagr.p95)} |\n| P(CAGR >= 50%) | ${pct(summary.distribution.probabilities.cagrGe50)} |\n| P(CAGR >= 80%) | ${pct(summary.distribution.probabilities.cagrGe80)} |\n| MaxDD median | ${pct(summary.distribution.maxDrawdown.median)} |\n| Adverse DD p5 | ${pct(summary.distribution.maxDrawdown.adverseP05)} |\n| P(MaxDD <= -30%) | ${pct(summary.distribution.probabilities.maxDdLe30)} |\n| P(MaxDD <= -40%) | ${pct(summary.distribution.probabilities.maxDdLe40)} |\n| P(MaxDD <= -50%) | ${pct(summary.distribution.probabilities.maxDdLe50)} |\n| Final wealth median | ${summary.distribution.finalWealth.median.toFixed(2)}x |\n| Median invested-month share | ${pct(summary.distribution.mechanics.medianInvestedMonthShare)} |\n| Mean QQQ-proxy imputation share | ${pct(summary.distribution.mechanics.meanImputedReturnShare)} |\n\n## Mechanics\n\nMedian exits/path: ${summary.distribution.mechanics.medianExits}; stop ${summary.distribution.mechanics.medianStopExits}; circuit ${summary.distribution.mechanics.medianCircuitExits}; market gate ${summary.distribution.mechanics.medianMarketExits}.\n\nThis simulation regenerates synthetic stock/QQQ OHLC paths with a common moving-block source index, rebuilds Top2 at each synthetic month-end, and passes every evaluation day through the Production state machine. Missing historical symbol returns are imputed with the same-day QQQ factor; the reported imputation share should therefore be treated as a model-risk diagnostic.\n`;
  const out = resolve("data/research/structural-monte-carlo");
  await mkdir(out, { recursive: true });
  await writeFile(resolve(out, "summary.json"), JSON.stringify(summary, null, 2) + "\n");
  await writeFile(resolve(out, "summary.md"), md);
  console.log(md);
  console.log(`RESULT_JSON=${JSON.stringify(summary)}`);
}

main().catch(err => { console.error(err); process.exitCode = 1; });
