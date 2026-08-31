import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, UniverseMonth } from "../src/lib/types";

type MarketFile = { histories: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type FrozenFile = { backtest?: { equityCurve: EquityPoint[] } };

type Trade = {
  entryDate: string;
  exitDate: string;
  symbols: string[];
  return: number;
  reason: string;
};

type Run = {
  curve: EquityPoint[];
  trades: Trade[];
  exposureDays: number;
  tradingDays: number;
};

const COST = 0.001;
const STOCK_SMA = 100;
const QQQ_SMA = 200;
const LOOKBACK = 5;
const HOLD_CLOSES = 5;
const STOP = 0.12;
const CIRCUIT = 0.12;

function mean(xs: number[]) {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN;
}

function quantile(xs: number[], q: number) {
  if (!xs.length) return NaN;
  const sorted = [...xs].sort((a, b) => a - b);
  const idx = (sorted.length - 1) * q;
  const lo = Math.floor(idx), hi = Math.ceil(idx);
  return lo === hi ? sorted[lo] : sorted[lo] * (hi - idx) + sorted[hi] * (idx - lo);
}

function correlation(a: number[], b: number[]) {
  const n = Math.min(a.length, b.length);
  if (n < 2) return NaN;
  const x = a.slice(0, n), y = b.slice(0, n);
  const mx = mean(x), my = mean(y);
  let num = 0, vx = 0, vy = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - mx, dy = y[i] - my;
    num += dx * dy; vx += dx * dx; vy += dy * dy;
  }
  return vx > 0 && vy > 0 ? num / Math.sqrt(vx * vy) : NaN;
}

function monthKey(date: string) { return date.slice(0, 7); }
function yearKey(date: string) { return date.slice(0, 4); }

function periodReturns(curve: EquityPoint[], keyFn: (date: string) => string) {
  const endByKey = new Map<string, EquityPoint>();
  for (const p of curve) endByKey.set(keyFn(p.date), p);
  const rows = [...endByKey.entries()].sort(([a], [b]) => a.localeCompare(b));
  const out = new Map<string, number>();
  for (let i = 1; i < rows.length; i++) out.set(rows[i][0], rows[i][1].equity / rows[i - 1][1].equity - 1);
  return out;
}

function rollingCompounded(monthly: Map<string, number>, months: number) {
  const rows = [...monthly.entries()].sort(([a], [b]) => a.localeCompare(b));
  const values: number[] = [];
  for (let i = months - 1; i < rows.length; i++) {
    let gross = 1;
    for (let j = i - months + 1; j <= i; j++) gross *= 1 + rows[j][1];
    values.push(gross - 1);
  }
  return values;
}

function latestUniverse(universeHistory: UniverseMonth[], date: string) {
  let found: UniverseMonth | null = null;
  for (const u of universeHistory) {
    if (u.asOf <= date) found = u;
    else break;
  }
  return found;
}

function runTcsr(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], ignoredSymbol?: string): Run {
  const qqq = [...(histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const dates = qqq.map((p) => p.date).filter((d) => d >= "2020-01-01");
  const maps = Object.fromEntries(Object.entries(histories).map(([s, pts]) => [s, new Map(pts.map((p) => [p.date, p]))]));
  const indexBySymbol = Object.fromEntries(Object.entries(histories).map(([s, pts]) => [s, new Map([...pts].sort((a,b)=>a.date.localeCompare(b.date)).map((p, i) => [p.date, i]))]));
  const sortedHistories = Object.fromEntries(Object.entries(histories).map(([s, pts]) => [s, [...pts].sort((a,b)=>a.date.localeCompare(b.date))]));

  let cash = 1;
  let positions: Array<{ symbol: string; shares: number; entryPrice: number }> = [];
  let entryEquity = 1;
  let peak = 1;
  let holdingCloses = 0;
  let pendingExit: { date: string; reason: string } | null = null;
  let pendingEntry: { date: string; symbols: string[] } | null = null;
  let exposureDays = 0;
  const trades: Trade[] = [];
  let tradeEntryDate = "";
  const curve: EquityPoint[] = [];

  const equityAt = (date: string, field: "open" | "close") => cash + positions.reduce((sum, p) => {
    const row = maps[p.symbol]?.get(date);
    const px = row?.[field] ?? row?.close ?? p.entryPrice;
    return sum + p.shares * px;
  }, 0);

  for (let di = 0; di < dates.length; di++) {
    const date = dates[di];
    const nextDate = dates[di + 1] ?? null;

    if (pendingExit?.date === date && positions.length) {
      const before = equityAt(date, "open");
      const proceeds = positions.reduce((sum, p) => {
        const row = maps[p.symbol]?.get(date);
        const px = row?.open ?? row?.close;
        return sum + (px ? p.shares * px : 0);
      }, 0);
      cash = proceeds * (1 - COST);
      trades.push({ entryDate: tradeEntryDate, exitDate: date, symbols: positions.map((p) => p.symbol), return: cash / entryEquity - 1, reason: pendingExit.reason });
      positions = [];
      holdingCloses = 0;
      pendingExit = null;
      peak = cash;
      if (!Number.isFinite(before)) throw new Error(`Invalid exit equity ${date}`);
    }

    if (pendingEntry?.date === date && !positions.length) {
      const opens = pendingEntry.symbols.map((s) => maps[s]?.get(date)?.open);
      if (opens.every((p): p is number => Boolean(p && p > 0))) {
        entryEquity = cash;
        const perName = cash / pendingEntry.symbols.length;
        positions = pendingEntry.symbols.map((symbol, i) => ({ symbol, entryPrice: opens[i], shares: perName * (1 - COST) / opens[i] }));
        cash = 0;
        tradeEntryDate = date;
        peak = equityAt(date, "open");
        holdingCloses = 0;
      }
      pendingEntry = null;
    }

    if (positions.length) exposureDays++;
    const closeEquity = equityAt(date, "close");
    peak = Math.max(peak, closeEquity);
    const dd = peak > 0 ? closeEquity / peak - 1 : 0;
    curve.push({ date, equity: closeEquity, drawdown: dd });

    if (positions.length && !pendingExit) {
      holdingCloses++;
      const stopped = positions.some((p) => {
        const close = maps[p.symbol]?.get(date)?.close;
        return close != null && close <= p.entryPrice * (1 - STOP);
      });
      if (nextDate && stopped) pendingExit = { date: nextDate, reason: "individual-stop" };
      else if (nextDate && dd <= -CIRCUIT) pendingExit = { date: nextDate, reason: "portfolio-circuit" };
      else if (nextDate && holdingCloses >= HOLD_CLOSES) pendingExit = { date: nextDate, reason: "scheduled-5-session-exit" };
    }

    if (!positions.length && !pendingEntry && nextDate) {
      const qIdx = indexBySymbol.QQQ?.get(date);
      if (qIdx == null || qIdx + 1 < QQQ_SMA) continue;
      const qRows = sortedHistories.QQQ as PricePoint[];
      const qClose = qRows[qIdx].close;
      const qSma = mean(qRows.slice(qIdx - QQQ_SMA + 1, qIdx + 1).map((p) => p.close));
      if (!(qClose > qSma)) continue;

      const u = latestUniverse(universeHistory, date);
      if (!u) continue;
      const candidates: Array<{ symbol: string; r5: number }> = [];
      for (const member of u.symbols) {
        const symbol = member.symbol;
        if (symbol === ignoredSymbol) continue;
        const idx = indexBySymbol[symbol]?.get(date);
        const rows = sortedHistories[symbol] as PricePoint[] | undefined;
        if (idx == null || !rows || idx < Math.max(STOCK_SMA - 1, LOOKBACK)) continue;
        const close = rows[idx].close;
        const sma100 = mean(rows.slice(idx - STOCK_SMA + 1, idx + 1).map((p) => p.close));
        const prior = rows[idx - LOOKBACK].close;
        const r5 = close / prior - 1;
        if (close > sma100 && r5 < 0) candidates.push({ symbol, r5 });
      }
      candidates.sort((a, b) => a.r5 - b.r5 || a.symbol.localeCompare(b.symbol));
      if (candidates.length >= 2) pendingEntry = { date: nextDate, symbols: candidates.slice(0, 2).map((x) => x.symbol) };
    }
  }

  return { curve, trades, exposureDays, tradingDays: dates.length };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const frozen = JSON.parse(await readFile(resolve("public/data/backtest-frozen.json"), "utf8")) as FrozenFile;
  const universeHistory = [...universe.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));

  const run = runTcsr(market.histories, universeHistory);
  const stats = performanceStats(run.curve);
  const tradeReturns = run.trades.map((t) => t.return);
  const tcsrMonthly = periodReturns(run.curve, monthKey);
  const fixedMonthly = periodReturns(frozen.backtest?.equityCurve ?? [], monthKey);
  const overlap = [...tcsrMonthly.keys()].filter((m) => fixedMonthly.has(m));
  const t = overlap.map((m) => tcsrMonthly.get(m)!);
  const f = overlap.map((m) => fixedMonthly.get(m)!);
  const negativeFixed = overlap.filter((m) => fixedMonthly.get(m)! < 0);
  const oppositePositive = negativeFixed.filter((m) => tcsrMonthly.get(m)! > 0);
  const worstFixed = [...overlap].sort((a,b)=>fixedMonthly.get(a)! - fixedMonthly.get(b)!).slice(0, 10);
  const yearly = periodReturns(run.curve, yearKey);
  const roll12 = rollingCompounded(tcsrMonthly, 12);
  const roll36 = rollingCompounded(tcsrMonthly, 36);

  const symbols = [...new Set(universeHistory.flatMap((u) => u.symbols.map((m) => m.symbol)))];
  const loo = symbols.map((symbol) => {
    const x = runTcsr(market.histories, universeHistory, symbol);
    return { symbol, cagr: performanceStats(x.curve).cagr };
  }).sort((a,b)=>a.cagr-b.cagr);
  const baseCagr = stats.cagr;
  const worstLoo = loo[0];

  const report = {
    preregisteredSpec: { qqqSma: QQQ_SMA, stockSma: STOCK_SMA, reversalSessions: LOOKBACK, holdCloses: HOLD_CLOSES, stop: STOP, circuit: CIRCUIT, topN: 2, costPerSide: COST },
    sample: { start: run.curve[0]?.date ?? null, end: run.curve.at(-1)?.date ?? null, tradingDays: run.tradingDays },
    stats,
    exposureShare: run.tradingDays ? run.exposureDays / run.tradingDays : 0,
    trades: {
      count: run.trades.length,
      perYear: run.curve.length > 1 ? run.trades.length / ((Date.parse(run.curve.at(-1)!.date) - Date.parse(run.curve[0].date)) / (365.25 * 86400000)) : 0,
      winRate: tradeReturns.length ? tradeReturns.filter((r) => r > 0).length / tradeReturns.length : 0,
      median: quantile(tradeReturns, 0.5),
      p10: quantile(tradeReturns, 0.1),
      worst: tradeReturns.length ? Math.min(...tradeReturns) : null,
    },
    yearly: Object.fromEntries(yearly),
    rolling12M: { median: quantile(roll12, 0.5), p10: quantile(roll12, 0.1), worst: roll12.length ? Math.min(...roll12) : null },
    rolling36M: { median: quantile(roll36, 0.5), p10: quantile(roll36, 0.1), worst: roll36.length ? Math.min(...roll36) : null },
    independence: {
      monthlyCorrelationWithFixed60: correlation(t, f),
      fixed60NegativeMonths: negativeFixed.length,
      positiveTcsrDuringFixed60NegativeMonths: oppositePositive.length,
      positiveShareDuringFixed60NegativeMonths: negativeFixed.length ? oppositePositive.length / negativeFixed.length : null,
      fixed60Worst10Months: worstFixed.map((m) => ({ month: m, fixed60: fixedMonthly.get(m), tcsr: tcsrMonthly.get(m) })),
    },
    concentration: {
      worstLoo,
      worstLooCagrRetention: worstLoo && baseCagr !== 0 ? worstLoo.cagr / baseCagr : null,
      bottom10Loo: loo.slice(0, 10),
    },
    stage1Pass: {
      cagr15: stats.cagr >= 0.15,
      maxDd40: stats.maxDrawdown > -0.40,
      correlation60: Number.isFinite(correlation(t, f)) && correlation(t, f) <= 0.60,
      defensive30: negativeFixed.length > 0 && oppositePositive.length / negativeFixed.length >= 0.30,
      looRetention50: Boolean(worstLoo) && (baseCagr <= 0 ? false : worstLoo!.cagr >= baseCagr * 0.5),
    },
  };

  console.log(JSON.stringify(report, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
