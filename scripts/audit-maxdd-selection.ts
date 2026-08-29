import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };

const FREEZE = "2026-08-24T09:58:16Z"; // PR #35 production migration commit time
const pct = (x: number) => `${(x * 100).toFixed(2)}%`;

function globalDd(curve: EquityPoint[]) {
  let peak = curve[0]?.equity ?? 1;
  let dd = 0;
  for (const p of curve) {
    peak = Math.max(peak, p.equity);
    dd = Math.min(dd, p.equity / peak - 1);
  }
  return dd;
}

function globalStats(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], config: StrategyConfig) {
  const bt = runBacktest({ histories, universeHistory, config });
  const maxDrawdown = globalDd(bt.equityCurve);
  return {
    cagr: bt.stats.cagr,
    globalMaxDrawdown: maxDrawdown,
    engineEpisodeMaxDrawdown: bt.stats.maxDrawdown,
    calmarGlobal: maxDrawdown < 0 ? bt.stats.cagr / Math.abs(maxDrawdown) : null,
    finalEquity: bt.stats.finalEquity,
    equityCurve: bt.equityCurve,
  };
}

function monthlyLogReturns(curve: EquityPoint[]) {
  const byMonth = new Map<string, EquityPoint>();
  for (const p of curve) byMonth.set(p.date.slice(0, 7), p);
  const rows = [...byMonth.values()];
  const out: number[] = [];
  let prev = 1;
  for (const p of rows) {
    if (prev > 0 && p.equity > 0) out.push(Math.log(p.equity / prev));
    prev = p.equity;
  }
  return out;
}

function neweyWestMeanSe(xs: number[], lag = 3) {
  const n = xs.length;
  const mean = xs.reduce((a, b) => a + b, 0) / n;
  const centered = xs.map((x) => x - mean);
  let longRunVar = centered.reduce((s, x) => s + x * x, 0) / n;
  for (let l = 1; l <= Math.min(lag, n - 1); l++) {
    let gamma = 0;
    for (let t = l; t < n; t++) gamma += centered[t] * centered[t - l];
    gamma /= n;
    const w = 1 - l / (lag + 1);
    longRunVar += 2 * w * gamma;
  }
  return Math.sqrt(Math.max(0, longRunVar) / n);
}

// Acklam-style inverse normal approximation.
function invNorm(p: number) {
  const a=[-3.969683028665376e1,2.209460984245205e2,-2.759285104469687e2,1.38357751867269e2,-3.066479806614716e1,2.506628277459239];
  const b=[-5.447609879822406e1,1.615858368580409e2,-1.556989798598866e2,6.680131188771972e1,-1.328068155288572e1];
  const c=[-7.784894002430293e-3,-3.223964580411365e-1,-2.400758277161838,-2.549732539343734,4.374664141464968,2.938163982698783];
  const d=[7.784695709041462e-3,3.224671290700398e-1,2.445134137142996,3.754408661907416];
  const plow=0.02425, phigh=1-plow;
  if(p<plow){const q=Math.sqrt(-2*Math.log(p));return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)}
  if(p>phigh){const q=Math.sqrt(-2*Math.log(1-p));return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)}
  const q=p-.5,r=q*q;return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
}

function expectedMaxZ(n: number) {
  // Blom approximation to expected maximum of n standard normals.
  return invNorm((n - 0.375) / (n + 0.25));
}

function git(args: string[]) {
  return execFileSync("git", args, { encoding: "utf8", maxBuffer: 20 * 1024 * 1024 }).trim();
}

function configSnapshotsFromHistory() {
  const log = git(["log", "--all", "--format=%H|%cI|%s", "--", "src/lib/config.ts"]);
  const rows: any[] = [];
  for (const line of log.split("\n").filter(Boolean)) {
    const [sha, date, ...rest] = line.split("|");
    let text = "";
    try { text = git(["show", `${sha}:src/lib/config.ts`]); } catch { continue; }
    const grab = (re: RegExp) => text.match(re)?.[1] ?? null;
    const snap = {
      topN: grab(/topN:\s*([0-9.]+)/),
      oneMonth: grab(/oneMonth:\s*([0-9.]+)/),
      threeMonth: grab(/threeMonth:\s*([0-9.]+)/),
      sixMonth: grab(/sixMonth:\s*([0-9.]+)/),
      surgeLimit: grab(/surgeLimit:\s*([0-9.]+)/),
      qqqMa: grab(/qqqMonthlyMaMonths:\s*([0-9.]+)/),
      stop: grab(/individualStop:\s*([0-9.]+)/),
      circuit: grab(/portfolioCircuit:\s*([0-9.]+)/),
      recovery: grab(/confirmationDays:\s*([0-9.]+)/),
    };
    rows.push({ sha, date, subject: rest.join("|"), preFreeze: date <= FREEZE, snapshot: snap });
  }
  const key = (x: any) => JSON.stringify(x.snapshot);
  const uniquePre = [...new Map(rows.filter(r => r.preFreeze).map(r => [key(r), r])).values()];
  const uniqueAll = [...new Map(rows.map(r => [key(r), r])).values()];
  return { rows, uniquePre, uniqueAll };
}

function researchBranchInventory() {
  let refs = "";
  try { refs = git(["for-each-ref", "--format=%(refname:short)|%(committerdate:iso-strict)|%(subject)", "refs/remotes/origin/research/"]); } catch { return []; }
  return refs.split("\n").filter(Boolean).map(line => {
    const [branch, date, ...subject] = line.split("|");
    return { branch, date, subject: subject.join("|"), preFreeze: date <= FREEZE };
  });
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as Market;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = market.histories;
  const universeHistory = universe.history;

  const configs: { family: string; label: string; config: StrategyConfig }[] = [];
  const add = (family: string, label: string, patch: Partial<StrategyConfig>) => configs.push({ family, label, config: { ...PRODUCTION_STRATEGY, ...patch } as StrategyConfig });
  configs.push({ family: "baseline", label: "Production", config: PRODUCTION_STRATEGY as StrategyConfig });
  for (const stop of [0.15, 0.20]) add("risk-stop", `Stop ${stop}`, { risk: { ...PRODUCTION_STRATEGY.risk, individualStop: stop } });
  for (const circuit of [0.125, 0.175]) add("risk-circuit", `Circuit ${circuit}`, { risk: { ...PRODUCTION_STRATEGY.risk, portfolioCircuit: circuit } });
  for (const days of [5, 15]) add("risk-recovery", `Recovery ${days}`, { recovery: { ...PRODUCTION_STRATEGY.recovery, confirmationDays: days } });
  for (const months of [6, 8, 12]) add("qqq-ma", `QQQ MA ${months}M`, { market: { ...PRODUCTION_STRATEGY.market, qqqMonthlyMaMonths: months } });
  for (const [threeMonth, sixMonth] of [[0.15,0.85],[0.25,0.75]] as const) add("momentum-weight", `${Math.round(threeMonth*100)}/${Math.round(sixMonth*100)}`, { momentum: { ...PRODUCTION_STRATEGY.momentum, threeMonth, sixMonth } });

  const rerun = configs.map(({family,label,config}) => {
    const s = globalStats(histories, universeHistory, config);
    return { family, label, cagr:s.cagr, globalMaxDrawdown:s.globalMaxDrawdown, engineEpisodeMaxDrawdown:s.engineEpisodeMaxDrawdown, calmarGlobal:s.calmarGlobal, finalEquity:s.finalEquity };
  });
  const prodFull = globalStats(histories, universeHistory, PRODUCTION_STRATEGY as StrategyConfig);

  const history = configSnapshotsFromHistory();
  const branches = researchBranchInventory();
  const logs = monthlyLogReturns(prodFull.equityCurve);
  const seMonthly = neweyWestMeanSe(logs, 3);
  const multiplicity = [2, 5, 10, 25, 50, 100].map(n => {
    const z = expectedMaxZ(n);
    const annualLogUplift = 12 * seMonthly * z;
    return { effectiveIndependentTrials:n, expectedMaxZ:z, annualLogGrowthOptimism:annualLogUplift, multiplicativeGrowthFactor:Math.exp(annualLogUplift) };
  });

  const result = {
    generatedAt: new Date().toISOString(), strategyId: PRODUCTION_STRATEGY.strategyId,
    maxDdAudit: { definition:"standard global peak-to-trough drawdown recomputed from equity", rerun },
    selectionAudit: {
      freezeTimestamp: FREEZE,
      uniqueCommittedConfigSnapshotsPreFreeze: history.uniquePre.length,
      uniqueCommittedConfigSnapshotsAllHistory: history.uniqueAll.length,
      configHistory: history.rows,
      researchBranchesVisible: branches.length,
      researchBranchesWithTipPreFreeze: branches.filter(b=>b.preFreeze).length,
      researchBranchesWithTipPostFreeze: branches.filter(b=>!b.preFreeze).length,
      caveat:"Counts are a documented lower bound. Deleted branches, local/uncommitted experiments, chat-only trials, and parameter values tested outside committed config.ts are not observable from Git history. Post-freeze diagnostic branches must not be counted as trials that selected the frozen Production strategy.",
      monthlyLogReturnCount: logs.length,
      neweyWestLag3MonthlyMeanSe: seMonthly,
      multiplicitySensitivity: multiplicity,
      multiplicityInterpretation:"Heuristic only: assumes N effectively independent candidate strategies with equal sampling noise. Real strategy trials are correlated, so raw trial count is not N_eff. This table is a sensitivity bound, not a corrected expected CAGR."
    }
  };

  const outDir=resolve("data/research/maxdd-selection-audit"); await mkdir(outDir,{recursive:true});
  await writeFile(resolve(outDir,"result.json"),JSON.stringify(result,null,2)+"\n");
  let md="# MaxDD + strategy-selection audit — 2026-08-29\n\n";
  md+="## 1. Standard global MaxDD re-audit\n\n| Family | Variant | CAGR | Global MaxDD | Old engine-episode DD | Global Calmar |\n|---|---|---:|---:|---:|---:|\n";
  for(const r of rerun) md+=`| ${r.family} | ${r.label} | ${pct(r.cagr)} | ${pct(r.globalMaxDrawdown)} | ${pct(r.engineEpisodeMaxDrawdown)} | ${r.calmarGlobal?.toFixed(2)??"n/a"} |\n`;
  md+="\nThe old `stats.maxDrawdown` is an engine/state-machine episode drawdown because the risk peak resets after recovery. It must not be reported as standard investment MaxDD.\n\n";
  md+="## 2. Strategy-selection / multiple-testing audit\n\n";
  md+=`- Freeze timestamp used: **${FREEZE}** (Production migration).\n`;
  md+=`- Distinct committed `+"`src/lib/config.ts`"+` parameter snapshots visible before freeze: **${history.uniquePre.length}**.\n`;
  md+=`- Distinct committed config snapshots over all refs/history: **${history.uniqueAll.length}**.\n`;
  md+=`- Visible research branches: **${branches.length}**; tip pre-freeze **${branches.filter(b=>b.preFreeze).length}**, tip post-freeze **${branches.filter(b=>!b.preFreeze).length}**.\n\n`;
  md+="These are **lower bounds, not the true number of trials**. Deleted/local/chat-only experiments cannot be recovered from Git. More importantly, post-freeze robustness research did not select the already-frozen Production strategy and should not be charged as pre-selection multiple testing.\n\n";
  md+="### Independent-trial sensitivity (heuristic)\n\n| Effective independent trials | Expected best-noise z | Annual log-growth optimism | Growth-factor equivalent |\n|---:|---:|---:|---:|\n";
  for(const x of multiplicity) md+=`| ${x.effectiveIndependentTrials} | ${x.expectedMaxZ.toFixed(2)} | ${pct(x.annualLogGrowthOptimism)} | ${x.multiplicativeGrowthFactor.toFixed(2)}x |\n`;
  md+="\nThis is deliberately not converted into a 'corrected CAGR'. Trial results are highly correlated and the true effective trial count is unknown. The correct conclusion is about **selection-risk magnitude**, not a point estimate.\n";
  await writeFile(resolve(outDir,"RESULT_SUMMARY.md"),md);
  console.log(md); console.log("RESULT_JSON="+JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exit(1)});
