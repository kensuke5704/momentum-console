import type { EquityPoint, ExpectedCagrModel } from "./types";

const BOOTSTRAP_BLOCK_SESSIONS = 63;
const BOOTSTRAP_RESAMPLES = 20_000;
const BOOTSTRAP_SEED = 60_202_608;

function mulberry32(seed: number) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
}

function quantile(sorted: number[], q: number): number {
  if (!sorted.length) return 0;
  const position = (sorted.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  const weight = position - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

/**
 * Rebuild the displayed CAGR distribution from the same equity curve shown in
 * the console. The bootstrap preserves local 63-session return blocks but is a
 * historical diagnostic, not a calibrated probability forecast.
 */
export function buildExpectedCagrModel(equityCurve: EquityPoint[], strategyId: string): ExpectedCagrModel | undefined {
  if (equityCurve.length < 3) return undefined;
  const logReturns = equityCurve.slice(1).map((point, index) => Math.log(point.equity / equityCurve[index].equity));
  const observations = logReturns.length;
  const block = Math.min(BOOTSTRAP_BLOCK_SESSIONS, observations);
  const blockStarts = observations - block + 1;
  if (blockStarts <= 0) return undefined;

  const prefix = [0];
  for (const value of logReturns) prefix.push(prefix.at(-1)! + value);
  const blockSum = (start: number, length: number) => prefix[start + length] - prefix[start];
  const random = mulberry32(BOOTSTRAP_SEED);
  const cagrSamples = new Array<number>(BOOTSTRAP_RESAMPLES);

  for (let sample = 0; sample < BOOTSTRAP_RESAMPLES; sample += 1) {
    let remaining = observations;
    let totalLogReturn = 0;
    while (remaining > 0) {
      const length = Math.min(block, remaining);
      const maxStart = observations - length + 1;
      const start = Math.floor(random() * maxStart);
      totalLogReturn += blockSum(start, length);
      remaining -= length;
    }
    cagrSamples[sample] = Math.exp(totalLogReturn * (252 / observations)) - 1;
  }
  cagrSamples.sort((a, b) => a - b);

  const months = new Set(equityCurve.map((point) => point.date.slice(0, 7))).size;
  return {
    generatedAt: new Date().toISOString(),
    sourceRun: "dashboard-derived",
    strategyId,
    method: "63-session moving-block bootstrap of the displayed strategy equity curve, 20,000 deterministic resamples; historical diagnostic, not a calibrated forecast",
    sample: {
      start: equityCurve[0].date,
      end: equityCurve.at(-1)!.date,
      tradingDays: equityCurve.length,
      months,
    },
    estimate: {
      point: quantile(cagrSamples, 0.5),
      central50: [quantile(cagrSamples, 0.25), quantile(cagrSamples, 0.75)],
      central90: [quantile(cagrSamples, 0.05), quantile(cagrSamples, 0.95)],
    },
  };
}

export type ExpectedCagrChartPoint = {
  date: string;
  strategy: number;
  expected: number;
  central50: [number, number];
  central90: [number, number];
};

export function buildExpectedCagrOverlay(equityCurve: EquityPoint[], model: ExpectedCagrModel): ExpectedCagrChartPoint[] {
  const first = equityCurve[0];
  if (!first) return [];
  const start = Date.parse(first.date);
  const projected = (cagr: number, years: number) => first.equity * (1 + cagr) ** years;
  return equityCurve.map((point) => {
    const years = Math.max(0, (Date.parse(point.date) - start) / (365.25 * 86_400_000));
    return {
      date: point.date,
      strategy: point.equity,
      expected: projected(model.estimate.point, years),
      central50: model.estimate.central50.map((cagr) => projected(cagr, years)) as [number, number],
      central90: model.estimate.central90.map((cagr) => projected(cagr, years)) as [number, number],
    };
  });
}
