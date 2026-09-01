import { performanceStats } from "./backtest";
import { PRODUCTION_PORTFOLIO } from "./portfolio-config";
import type { BacktestResult, EquityPoint, ForwardOosResult } from "./types";

// Stage21 rounded v1 was production-approved after the SBI whole-share account
// realism audit. Its Forward OOS clock is separate from legacy Fixed60 OOS.
export const OOS_START_DATE = PRODUCTION_PORTFOLIO.oosStartDate;

export function emptyForwardOos(strategyId: string): ForwardOosResult {
  const equityCurve: EquityPoint[] = [{ date: OOS_START_DATE, equity: 1, drawdown: 0 }];
  return {
    strategyId,
    startedAt: OOS_START_DATE,
    asOf: null,
    source: "Yahoo Finance adjusted OHLC",
    baselineBacktestEquity: null,
    equityCurve,
    stats: performanceStats(equityCurve),
    records: [],
  };
}

export function updateForwardOos(backtest: BacktestResult, existing?: ForwardOosResult | null, provisionalDates: string[] = []): ForwardOosResult {
  const compatible = existing?.strategyId === backtest.strategyId && existing.startedAt === OOS_START_DATE;
  const prior = compatible ? existing : emptyForwardOos(backtest.strategyId);
  const actual = backtest.equityCurve.filter((point) => point.date >= OOS_START_DATE);
  const baseline = prior.baselineBacktestEquity ?? actual[0]?.equity ?? null;
  const byDate = new Map(prior.equityCurve.map((point) => [point.date, point]));
  const previouslyProvisional = new Set(prior.provisionalDates ?? []);
  const currentlyProvisional = new Set(provisionalDates);

  if (baseline != null) {
    for (const point of actual) {
      if (!byDate.has(point.date) || previouslyProvisional.has(point.date)) {
        byDate.set(point.date, { date: point.date, equity: point.equity / baseline, drawdown: 0 });
      }
    }
  }

  let peak = 0;
  const equityCurve = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date)).map((point) => {
    peak = Math.max(peak, point.equity);
    return { ...point, drawdown: peak > 0 ? point.equity / peak - 1 : 0 };
  });
  const lastActual = actual.at(-1)?.date ?? prior.asOf;
  return {
    ...prior,
    strategyId: backtest.strategyId,
    startedAt: OOS_START_DATE,
    asOf: lastActual ?? null,
    source: provisionalDates.length ? "Yahoo Finance adjusted OHLC + validated regular-session close" : "Yahoo Finance adjusted OHLC",
    baselineBacktestEquity: baseline,
    equityCurve,
    stats: performanceStats(equityCurve),
    provisionalDates: [...currentlyProvisional].filter((date) => byDate.has(date)).sort(),
  };
}
