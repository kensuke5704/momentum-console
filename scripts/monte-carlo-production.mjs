import { readFile, mkdir, writeFile } from "node:fs/promises";

const DASHBOARD_PATH = new URL("../public/data/dashboard.json", import.meta.url);
const OUT_DIR = new URL("../data/research/monte-carlo/", import.meta.url);
const OUT_JSON = new URL("production-5y-50000.json", OUT_DIR);
const OUT_MD = new URL("production-5y-50000.md", OUT_DIR);

const PATHS = 50_000;
const YEARS = 5;
const TRADING_DAYS_PER_YEAR = 252;
const HORIZON = YEARS * TRADING_DAYS_PER_YEAR;
const BLOCK = 20;
const SEED = 20260825;

function rngFactory(seed) {
  let x = seed >>> 0 || 1;
  return () => {
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    return (x >>> 0) / 4294967296;
  };
}

function quantile(sorted, q) {
  if (!sorted.length) return null;
  const x = (sorted.length - 1) * q;
  const lo = Math.floor(x), hi = Math.ceil(x);
  if (lo === hi) return sorted[lo];
  return sorted[lo] * (hi - x) + sorted[hi] * (x - lo);
}

function pct(x) { return `${(x * 100).toFixed(2)}%`; }
function xfmt(x) { return `${x.toFixed(2)}x`; }

function summarize(cagrs, dds, wealths) {
  const c = [...cagrs].sort((a,b)=>a-b);
  const d = [...dds].sort((a,b)=>a-b);
  const w = [...wealths].sort((a,b)=>a-b);
  const prob = (arr, fn) => arr.reduce((n,x)=>n+(fn(x)?1:0),0)/arr.length;
  return {
    cagr: { p05: quantile(c,.05), p25: quantile(c,.25), median: quantile(c,.50), p75: quantile(c,.75), p95: quantile(c,.95) },
    maxDrawdown: { adverseP05: quantile(d,.05), p25: quantile(d,.25), median: quantile(d,.50), p75: quantile(d,.75), p95: quantile(d,.95) },
    finalWealth: { p05: quantile(w,.05), p25: quantile(w,.25), median: quantile(w,.50), p75: quantile(w,.75), p95: quantile(w,.95) },
    probabilities: {
      cagrGe50: prob(cagrs,x=>x>=.50),
      cagrGe80: prob(cagrs,x=>x>=.80),
      cagrLt0: prob(cagrs,x=>x<0),
      maxDdLe30: prob(dds,x=>x<=-.30),
      maxDdLe40: prob(dds,x=>x<=-.40),
      maxDdLe50: prob(dds,x=>x<=-.50),
      finalWealthLt1: prob(wealths,x=>x<1),
    }
  };
}

function simulate(returns, shock = null, seedOffset = 0) {
  if (returns.length < BLOCK) throw new Error(`Need at least ${BLOCK} daily returns`);
  const rng = rngFactory(SEED + seedOffset);
  const cagrs = new Float64Array(PATHS);
  const dds = new Float64Array(PATHS);
  const wealths = new Float64Array(PATHS);
  const maxStart = returns.length - BLOCK;

  for (let p=0; p<PATHS; p++) {
    let wealth=1, peak=1, maxDd=0, day=0;
    const shockDay = shock == null ? -1 : Math.floor(rng()*HORIZON);
    while (day < HORIZON) {
      const start = Math.floor(rng()*(maxStart+1));
      const n = Math.min(BLOCK,HORIZON-day);
      for (let j=0;j<n;j++) {
        let factor=1+returns[start+j];
        if (day+j===shockDay) factor *= 1+shock;
        wealth *= Math.max(0.000001,factor);
        if (wealth>peak) peak=wealth;
        const dd=wealth/peak-1;
        if (dd<maxDd) maxDd=dd;
      }
      day += n;
    }
    wealths[p]=wealth;
    cagrs[p]=Math.pow(wealth,1/YEARS)-1;
    dds[p]=maxDd;
  }
  return summarize(cagrs,dds,wealths);
}

const raw = JSON.parse(await readFile(DASHBOARD_PATH,"utf8"));
const dashboard = raw.dashboard ?? raw;
const curve = dashboard.backtest?.equityCurve ?? [];
if (curve.length < 2) throw new Error("Production backtest equityCurve is empty");
const returns=[];
for (let i=1;i<curve.length;i++) {
  const prior=curve[i-1].equity, current=curve[i].equity;
  if (Number.isFinite(prior)&&prior>0&&Number.isFinite(current)&&current>0) returns.push(current/prior-1);
}
const first=curve[0], last=curve.at(-1);
const years=(Date.parse(last.date)-Date.parse(first.date))/(365.25*86400000);
const observedCagr=Math.pow(last.equity/first.equity,1/years)-1;
const observedStats=dashboard.backtest.stats;

const scenarios = {
  base: {
    label:"20-day moving-block bootstrap",
    shock:null,
    result:simulate(returns,null,0)
  },
  forcedSingleName30Gap: {
    label:"Base + one forced -30% Top1 single-name gap per 5 years (70% sleeve => -21% portfolio shock)",
    shock:-.21,
    result:simulate(returns,-.21,1000)
  },
  forcedSingleName50Gap: {
    label:"Base + one forced -50% Top1 single-name gap per 5 years (70% sleeve => -35% portfolio shock)",
    shock:-.35,
    result:simulate(returns,-.35,2000)
  }
};

const output={
  generatedAt:new Date().toISOString(),
  strategyId:dashboard.config?.strategyId,
  source:{dashboardGeneratedAt:dashboard.generatedAt,curveStart:first.date,curveEnd:last.date,dailyObservations:curve.length,dailyReturns:returns.length,reportedStats:observedStats,observedCagrFromCurve:observedCagr},
  methodology:{paths:PATHS,years:YEARS,horizonTradingDays:HORIZON,blockTradingDays:BLOCK,seed:SEED,notes:["Moving-block bootstrap resamples contiguous 20-trading-day strategy-return blocks with replacement.","Stress scenarios force one additional portfolio shock in every five-year path; they are severity tests, not estimates of event frequency.","Because the source sample begins in 2020, regime coverage is limited even though the Production state machine itself includes stop/circuit/recovery logic in the source returns."]},
  scenarios
};

await mkdir(OUT_DIR,{recursive:true});
await writeFile(OUT_JSON,JSON.stringify(output,null,2)+"\n");
let md=`# Production Monte Carlo — 5y / 50,000 paths\n\n`;
md+=`Strategy: **${output.strategyId}**  \nSource curve: **${first.date} → ${last.date}** (${curve.length} daily points)  \nReported CAGR: **${pct(observedStats.cagr)}** / recomputed from curve: **${pct(observedCagr)}**  \nReported MaxDD: **${pct(observedStats.maxDrawdown)}**\n\n`;
md+=`Method: 20-trading-day moving-block bootstrap, 5 years (1,260 sessions), 50,000 paths, seed ${SEED}.\n\n`;
md+=`| Scenario | CAGR p5 | CAGR median | CAGR p95 | P(CAGR≥50%) | P(CAGR≥80%) | MaxDD median | adverse DD p5 | P(DD≤-30%) | P(DD≤-40%) | Final wealth median |\n`;
md+=`|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n`;
for (const s of Object.values(scenarios)) {
  const r=s.result;
  md+=`| ${s.label} | ${pct(r.cagr.p05)} | ${pct(r.cagr.median)} | ${pct(r.cagr.p95)} | ${pct(r.probabilities.cagrGe50)} | ${pct(r.probabilities.cagrGe80)} | ${pct(r.maxDrawdown.median)} | ${pct(r.maxDrawdown.adverseP05)} | ${pct(r.probabilities.maxDdLe30)} | ${pct(r.probabilities.maxDdLe40)} | ${xfmt(r.finalWealth.median)} |\n`;
}
md+=`\n## Interpretation guardrails\n\n- Base bootstrap preserves roughly one month of serial dependence but does not create new market regimes absent from 2020-present data.\n- Forced gap scenarios are deliberately conservative severity overlays: every simulated 5-year path receives exactly one such shock.\n- The simulation resamples realized Production strategy returns; it does not rerun synthetic stock prices through the state machine, so it is a distributional robustness test rather than a structural market model.\n`;
await writeFile(OUT_MD,md);
console.log(md);
console.log(`RESULT_JSON=${JSON.stringify(output)}`);
