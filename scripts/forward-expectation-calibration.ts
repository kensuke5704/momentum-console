import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, UniverseMonth } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UF = { history: UniverseMonth[] };

type WindowRow = {
  months: number;
  start: string;
  end: string;
  cagr: number;
  maxDrawdown: number;
  startEquity: number;
  endEquity: number;
};

const quantile = (values: number[], p: number) => {
  if (!values.length) return null;
  const xs = [...values].sort((a, b) => a - b);
  const x = (xs.length - 1) * p;
  const lo = Math.floor(x), hi = Math.ceil(x);
  if (lo === hi) return xs[lo];
  return xs[lo] + (xs[hi] - xs[lo]) * (x - lo);
};

function monthlyLastPoints(curve: EquityPoint[]) {
  const map = new Map<string, EquityPoint>();
  for (const p of curve) map.set(p.date.slice(0, 7), p);
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([month, point]) => ({ month, point }));
}

function globalMaxDrawdown(points: EquityPoint[]) {
  let peak = -Infinity, dd = 0;
  for (const p of points) {
    peak = Math.max(peak, p.equity);
    dd = Math.min(dd, p.equity / peak - 1);
  }
  return dd;
}

function buildWindows(curve: EquityPoint[], months: number): WindowRow[] {
  const monthly = monthlyLastPoints(curve);
  const rows: WindowRow[] = [];
  for (let i = 0; i + months < monthly.length; i++) {
    const a = monthly[i].point;
    const b = monthly[i + months].point;
    const daily = curve.filter((p) => p.date >= a.date && p.date <= b.date);
    rows.push({
      months,
      start: a.date,
      end: b.date,
      cagr: (b.equity / a.equity) ** (12 / months) - 1,
      maxDrawdown: globalMaxDrawdown(daily),
      startEquity: a.equity,
      endEquity: b.equity,
    });
  }
  return rows;
}

function nonOverlapping(rows: WindowRow[]) {
  if (!rows.length) return [];
  const out: WindowRow[] = [];
  let lastEnd = "";
  for (const row of rows) {
    if (!lastEnd || row.start >= lastEnd) {
      out.push(row);
      lastEnd = row.end;
    }
  }
  return out;
}

function summarize(rows: WindowRow[]) {
  const c = rows.map((r) => r.cagr), d = rows.map((r) => r.maxDrawdown);
  return {
    n: rows.length,
    cagr: {
      min: c.length ? Math.min(...c) : null,
      p10: quantile(c, 0.10),
      p25: quantile(c, 0.25),
      median: quantile(c, 0.50),
      p75: quantile(c, 0.75),
      p90: quantile(c, 0.90),
      max: c.length ? Math.max(...c) : null,
    },
    maxDrawdown: {
      worst: d.length ? Math.min(...d) : null,
      p25: quantile(d, 0.25),
      median: quantile(d, 0.50),
      p75: quantile(d, 0.75),
      best: d.length ? Math.max(...d) : null,
    },
    probabilities: {
      cagrLt0: c.length ? c.filter((x) => x < 0).length / c.length : null,
      cagrGe15: c.length ? c.filter((x) => x >= 0.15).length / c.length : null,
      cagrGe20: c.length ? c.filter((x) => x >= 0.20).length / c.length : null,
      cagrGe25: c.length ? c.filter((x) => x >= 0.25).length / c.length : null,
      cagrGe30: c.length ? c.filter((x) => x >= 0.30).length / c.length : null,
    },
  };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as Market;
  const uf = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UF;
  const bt = runBacktest({ histories: market.histories, universeHistory: uf.history, config: PRODUCTION_STRATEGY });
  const horizons = [12, 24, 36];
  const horizonResults = horizons.map((months) => {
    const rolling = buildWindows(bt.equityCurve, months);
    const nonOverlap = nonOverlapping(rolling);
    return { months, rolling: summarize(rolling), nonOverlapping: summarize(nonOverlap), rows: rolling };
  });
  const result = {
    generatedAt: new Date().toISOString(),
    strategyId: PRODUCTION_STRATEGY.strategyId,
    purpose: "Empirical forward-return calibration using actual chronology only; no resampling and no parameter optimization.",
    fullHistory: {
      cagr: bt.stats.cagr,
      engineEpisodeMaxDrawdown: bt.stats.maxDrawdown,
      finalEquity: bt.stats.finalEquity,
    },
    horizons: horizonResults,
  };
  await mkdir(resolve("data/research/forward-expectation-calibration"), { recursive: true });
  await writeFile(resolve("data/research/forward-expectation-calibration/result.json"), JSON.stringify(result, null, 2) + "\n");
  const pct = (x: number | null) => x == null ? "n/a" : `${(x * 100).toFixed(2)}%`;
  let md = "# Forward expectation calibration\n\nActual chronology only. No CPCM / bootstrap / reshuffling. Production parameters are frozen.\n\n";
  md += "| Horizon | Sample | N | CAGR p10 | CAGR p25 | Median | p75 | p90 | Worst DD | P(CAGR<0) | P(CAGR>=20%) |\n|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n";
  for (const h of horizonResults) for (const [label, s] of [["rolling", h.rolling], ["non-overlap", h.nonOverlapping]] as const) {
    md += `| ${h.months}m | ${label} | ${s.n} | ${pct(s.cagr.p10)} | ${pct(s.cagr.p25)} | ${pct(s.cagr.median)} | ${pct(s.cagr.p75)} | ${pct(s.cagr.p90)} | ${pct(s.maxDrawdown.worst)} | ${pct(s.probabilities.cagrLt0)} | ${pct(s.probabilities.cagrGe20)} |\n`;
  }
  await writeFile(resolve("data/research/forward-expectation-calibration/result.md"), md);
  console.log(md);
  console.log("RESULT_JSON=" + JSON.stringify(result));
}

main().catch((e) => { console.error(e); process.exit(1); });
