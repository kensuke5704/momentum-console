import type { EquityPoint, ExpectedCagrModel } from "./types";

export const EXPECTED_CAGR_MODEL: ExpectedCagrModel = {
  generatedAt: "2026-08-25T15:06:17.831Z",
  sourceRun: "32863633662",
  strategyId: "momentum-dynamic-2026-08-v1",
  method: "3-month moving-block bootstrap, 20,000 resamples",
  sample: {
    start: "2020-01-02",
    end: "2026-08-25",
    tradingDays: 1670,
    months: 80,
  },
  estimate: {
    point: 0.4195844155287156,
    central50: [0.30063965968929685, 0.5788668662997956],
    central90: [0.11857228485506391, 0.8097196771762591],
  },
};

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
