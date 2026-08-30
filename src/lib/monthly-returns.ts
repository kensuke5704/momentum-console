import type { EquityPoint } from "./types";

export type MonthlyReturnHistogramBin = {
  label: string;
  from: number;
  to: number;
  probability: number;
  count: number;
};

export type MonthlyReturnDistribution = {
  sampleStart: string | null;
  sampleEnd: string | null;
  months: number;
  returns: number[];
  histogram5Pct: MonthlyReturnHistogramBin[];
  negativeProbability: number;
  zeroProbability: number;
  positiveProbability: number;
};

const BIN_WIDTH = 0.05;
const EPS = 1e-12;

function monthEndEquity(curve: EquityPoint[]): EquityPoint[] {
  const byMonth = new Map<string, EquityPoint>();
  for (const point of [...curve].sort((a, b) => a.date.localeCompare(b.date))) byMonth.set(point.date.slice(0, 7), point);
  return [...byMonth.values()];
}

function pctLabel(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function buildMonthlyReturnDistribution(curve: EquityPoint[]): MonthlyReturnDistribution {
  const monthEnds = monthEndEquity(curve);
  const returns = monthEnds.slice(1).flatMap((point, index) => {
    const prior = monthEnds[index];
    if (!(prior.equity > 0) || !(point.equity > 0)) return [];
    return [point.equity / prior.equity - 1];
  });
  const months = returns.length;
  if (!months) {
    return {
      sampleStart: monthEnds.at(0)?.date ?? null,
      sampleEnd: monthEnds.at(-1)?.date ?? null,
      months: 0,
      returns: [],
      histogram5Pct: [],
      negativeProbability: 0,
      zeroProbability: 0,
      positiveProbability: 0,
    };
  }

  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const start = Math.floor(min / BIN_WIDTH) * BIN_WIDTH;
  const end = Math.max(start + BIN_WIDTH, Math.ceil((max + EPS) / BIN_WIDTH) * BIN_WIDTH);
  const bins: MonthlyReturnHistogramBin[] = [];
  for (let rawFrom = start; rawFrom < end - EPS; rawFrom += BIN_WIDTH) {
    const from = Math.abs(rawFrom) < EPS ? 0 : rawFrom;
    const to = from + BIN_WIDTH;
    bins.push({ label: `${pctLabel(from)}–${pctLabel(to)}`, from, to, probability: 0, count: 0 });
  }

  for (const value of returns) {
    const index = Math.min(bins.length - 1, Math.max(0, Math.floor((value - start) / BIN_WIDTH + EPS)));
    bins[index].count += 1;
  }
  for (const bin of bins) bin.probability = bin.count / months;

  const negative = returns.filter((value) => value < -EPS).length;
  const zero = returns.filter((value) => Math.abs(value) <= EPS).length;
  const positive = months - negative - zero;
  return {
    sampleStart: monthEnds[0]?.date ?? null,
    sampleEnd: monthEnds.at(-1)?.date ?? null,
    months,
    returns,
    histogram5Pct: bins,
    negativeProbability: negative / months,
    zeroProbability: zero / months,
    positiveProbability: positive / months,
  };
}
