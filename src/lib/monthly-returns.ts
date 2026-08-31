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

function makeBin(label: string, from: number, to: number): MonthlyReturnHistogramBin {
  return { label, from, to, probability: 0, count: 0 };
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

  const negativeValues = returns.filter((value) => value < -EPS);
  const positiveValues = returns.filter((value) => value > EPS);
  const negativeStart = negativeValues.length
    ? Math.floor(Math.min(...negativeValues) / BIN_WIDTH) * BIN_WIDTH
    : 0;
  const positiveEnd = positiveValues.length
    ? Math.max(BIN_WIDTH, Math.ceil((Math.max(...positiveValues) + EPS) / BIN_WIDTH) * BIN_WIDTH)
    : 0;

  const negativeBins: MonthlyReturnHistogramBin[] = [];
  for (let rawFrom = negativeStart; rawFrom < -EPS; rawFrom += BIN_WIDTH) {
    const from = Math.abs(rawFrom) < EPS ? 0 : rawFrom;
    const to = Math.min(0, from + BIN_WIDTH);
    const label = to === 0 ? `${pctLabel(from)}–<0%` : `${pctLabel(from)}–${pctLabel(to)}`;
    negativeBins.push(makeBin(label, from, to));
  }

  const zeroBin = makeBin("0%", -EPS, EPS);

  const positiveBins: MonthlyReturnHistogramBin[] = [];
  for (let from = 0; from < positiveEnd - EPS; from += BIN_WIDTH) {
    const to = from + BIN_WIDTH;
    const label = from === 0 ? `>0%–${pctLabel(to)}` : `${pctLabel(from)}–${pctLabel(to)}`;
    positiveBins.push(makeBin(label, from, to));
  }

  for (const value of returns) {
    if (Math.abs(value) <= EPS) {
      zeroBin.count += 1;
      continue;
    }
    if (value < 0) {
      const index = Math.min(
        negativeBins.length - 1,
        Math.max(0, Math.floor((value - negativeStart) / BIN_WIDTH + EPS)),
      );
      negativeBins[index].count += 1;
      continue;
    }
    const index = Math.min(
      positiveBins.length - 1,
      Math.max(0, Math.floor(value / BIN_WIDTH + EPS)),
    );
    positiveBins[index].count += 1;
  }

  const bins = [...negativeBins, zeroBin, ...positiveBins];
  for (const bin of bins) bin.probability = bin.count / months;

  const negative = negativeValues.length;
  const zero = zeroBin.count;
  const positive = positiveValues.length;
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
