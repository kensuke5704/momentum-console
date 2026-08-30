import { PRODUCTION_STRATEGY } from "../config";
import type { MomentumCandidate, MonthlySignal, PricePoint, StrategyConfig, UniverseMonth } from "../types";

const monthKey = (date: string) => date.slice(0, 7);

export function monthlyCloses(points: PricePoint[]): PricePoint[] {
  const byMonth = new Map<string, PricePoint>();
  for (const point of [...points].sort((a, b) => a.date.localeCompare(b.date))) byMonth.set(monthKey(point.date), point);
  return [...byMonth.values()];
}

function returnAt(points: PricePoint[], signalDate: string, months: number): number | null {
  const closes = monthlyCloses(points).filter((point) => point.date <= signalDate);
  if (closes.length <= months) return null;
  const current = closes.at(-1)?.close;
  const prior = closes.at(-(months + 1))?.close;
  return current && prior ? current / prior - 1 : null;
}

function average(values: number[]): number { return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0; }
function populationStdDev(values: number[]): number {
  if (!values.length) return 0;
  const mean = average(values);
  return Math.sqrt(average(values.map((value) => (value - mean) ** 2)));
}

export function momentumScore(oneMonth: number, threeMonth: number, sixMonth: number, config: StrategyConfig = PRODUCTION_STRATEGY): number {
  return config.momentum.oneMonth * oneMonth + config.momentum.threeMonth * threeMonth + config.momentum.sixMonth * sixMonth;
}

export function qqqMonthlyGate(points: PricePoint[], signalDate: string, config: StrategyConfig = PRODUCTION_STRATEGY): { riskOn: boolean; close: number | null; ma: number | null } {
  const closes = monthlyCloses(points).filter((point) => point.date <= signalDate);
  const window = closes.slice(-config.market.qqqMonthlyMaMonths);
  if (window.length < config.market.qqqMonthlyMaMonths) return { riskOn: false, close: closes.at(-1)?.close ?? null, ma: null };
  const close = window.at(-1)?.close ?? null;
  const ma = average(window.map((point) => point.close));
  return { riskOn: close !== null && close > ma, close, ma };
}

export function buildMonthlySignal(args: {
  universe: UniverseMonth;
  histories: Record<string, PricePoint[]>;
  qqq: PricePoint[];
  nextSessionDate: string | null;
  config?: StrategyConfig;
}): MonthlySignal {
  const config = args.config ?? PRODUCTION_STRATEGY;
  const signalDate = args.universe.asOf;
  const gate = qqqMonthlyGate(args.qqq, signalDate, config);
  const q1 = returnAt(args.qqq, signalDate, 1);
  const q3 = returnAt(args.qqq, signalDate, 3);
  const q6 = returnAt(args.qqq, signalDate, 6);
  const qqqScore = q1 === null || q3 === null || q6 === null ? null : momentumScore(q1, q3, q6, config);

  const candidates: MomentumCandidate[] = args.universe.symbols.map(({ symbol }) => {
    const history = args.histories[symbol] ?? [];
    const oneMonth = returnAt(history, signalDate, 1);
    const threeMonth = returnAt(history, signalDate, 3);
    const sixMonth = returnAt(history, signalDate, 6);
    if (oneMonth === null || threeMonth === null || sixMonth === null || qqqScore === null) return { symbol, oneMonth, threeMonth, sixMonth, score: null, qqqScore, scoreSpread: null, eligible: false, exclusionReason: "INSUFFICIENT_PRICE_HISTORY", rank: null };
    const score = momentumScore(oneMonth, threeMonth, sixMonth, config);
    const exclusionReason = oneMonth >= config.momentum.surgeLimit ? "ONE_MONTH_SURGE" : config.momentum.requireAboveQqqScore && score <= qqqScore ? "NOT_ABOVE_QQQ" : null;
    return { symbol, oneMonth, threeMonth, sixMonth, score, qqqScore, scoreSpread: score - qqqScore, eligible: exclusionReason === null, exclusionReason, rank: null };
  });
  const eligible = candidates.filter((row): row is MomentumCandidate & { score: number } => row.eligible && row.score !== null).sort((a, b) => b.score - a.score || a.symbol.localeCompare(b.symbol));
  eligible.forEach((row, index) => { row.rank = index + 1; });
  const selected = gate.riskOn ? eligible.slice(0, config.selection.topN) : [];
  const validSelection = selected.length === config.selection.topN;
  const dispersion = populationStdDev(eligible.map((row) => row.score));
  const zGap = validSelection && dispersion > 0 ? (selected[0].score - selected[1].score) / dispersion : validSelection ? 0 : null;
  const concentrated = zGap !== null && zGap >= config.allocation.concentrationZGap;
  const top1 = Math.min(config.allocation.maxTop1Weight, concentrated ? config.allocation.concentratedTop1Weight : config.allocation.baseTop1Weight);
  const allocationMode: MonthlySignal["allocationMode"] = !validSelection
    ? "CASH"
    : Math.abs(top1 - 0.6) < 1e-12
      ? "60/40"
      : concentrated
        ? "70/30"
        : "50/50";
  return {
    strategyId: config.strategyId,
    signalMonth: args.universe.signalMonth,
    signalDate,
    executionDate: args.nextSessionDate,
    marketRiskOn: gate.riskOn,
    qqqClose: gate.close,
    qqqMonthlyMa: gate.ma,
    qqqScore,
    universe: args.universe.symbols.map((row) => row.symbol),
    candidates: candidates.sort((a, b) => (a.rank ?? 9999) - (b.rank ?? 9999) || (b.score ?? -Infinity) - (a.score ?? -Infinity)),
    selectedSymbols: validSelection ? selected.map((row) => row.symbol) : [],
    targetWeights: validSelection ? [top1, 1 - top1] : [],
    zGap,
    allocationMode,
  };
}
