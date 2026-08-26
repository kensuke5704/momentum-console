export type PricePoint = { date: string; open: number; close: number; high?: number; low?: number };

export type StrategyConfig = {
  strategyId: string;
  universe: { size: number; mode: "sec-nport-breadth" };
  momentum: { oneMonth: number; threeMonth: number; sixMonth: number; surgeLimit: number; requireAboveQqqScore: boolean };
  selection: { topN: 2 };
  allocation: { baseTop1Weight: number; concentratedTop1Weight: number; concentrationZGap: number; maxTop1Weight: number };
  market: { qqqMonthlyMaMonths: number };
  risk: { individualStop: number; portfolioCircuit: number };
  recovery: { qqqDailySmaDays: number; qqqMomentumDays: number; confirmationDays: number };
  execution: { entry: "next-session-open"; exit: "next-session-open"; transactionCost: number };
  backtestStart: string;
};

export type UniverseHolding = { symbol: string; issuerName?: string; weight: number };
export type NportFiling = { accession: string; seriesId: string; seriesName: string; reportDate: string; filingDate: string; holdings: UniverseHolding[] };
export type UniverseMember = { symbol: string; universeRank: number; etfCount: number; aggregateWeight: number; maxWeight: number; recencyWeight: number; universeScore: number };
export type UniverseMonth = {
  signalMonth: string;
  asOf: string;
  symbols: UniverseMember[];
  sourceFilings: Array<{ accession: string; seriesId: string; seriesName: string; filingDate: string }>;
  added: string[];
  removed: string[];
};

export type MomentumCandidate = {
  symbol: string;
  oneMonth: number | null;
  threeMonth: number | null;
  sixMonth: number | null;
  score: number | null;
  qqqScore: number | null;
  scoreSpread: number | null;
  eligible: boolean;
  exclusionReason: string | null;
  rank: number | null;
};
export type MonthlySignal = {
  strategyId: string;
  signalMonth: string;
  signalDate: string;
  executionDate: string | null;
  marketRiskOn: boolean;
  qqqClose: number | null;
  qqqMonthlyMa: number | null;
  qqqScore: number | null;
  universe: string[];
  candidates: MomentumCandidate[];
  selectedSymbols: string[];
  targetWeights: number[];
  zGap: number | null;
  allocationMode: "CASH" | "50/50" | "70/30";
};

export type RiskState = "INVESTED" | "LOCKED_MARKET" | "LOCKED_STOP" | "LOCKED_CIRCUIT" | "WAITING_RECOVERY" | "READY_NEXT_OPEN" | "CASH";
export type NextActionType = "BUY_NEXT_OPEN" | "SELL_ALL_NEXT_OPEN" | "HOLD" | "CASH_RECOVERY" | "MONTH_END_REBALANCE_NEXT_OPEN" | "CASH";
export type PositionState = { symbol: string; shares: number; entryPrice: number; targetWeight: number; currentPrice: number | null; stopLevel: number };
export type LiveStrategyState = {
  strategyId: string;
  asOf: string;
  state: RiskState;
  cash: number;
  currentPositions: PositionState[];
  portfolioPeak: number;
  currentEquity: number;
  drawdown: number;
  recoveryConsecutiveDays: number;
  lastTrigger: string | null;
  pendingSignal: MonthlySignal | null;
  nextAction: { type: NextActionType; executionDate: string | null; symbols: string[]; targetWeights: number[]; reason: string };
};

export type EquityPoint = { date: string; equity: number; drawdown: number };
export type PerformanceStats = { cagr: number; maxDrawdown: number; annualizedVolatility: number; calmar: number | null; finalEquity: number };
export type ExpectedCagrModel = {
  generatedAt: string;
  sourceRun: string;
  strategyId: string;
  method: string;
  sample: { start: string; end: string; tradingDays: number; months: number };
  estimate: { point: number; central50: [number, number]; central90: [number, number] };
};
export type BacktestResult = {
  strategyId: string;
  equityCurve: EquityPoint[];
  stats: PerformanceStats;
  benchmark: { label: "TQQQ Buy & Hold" | "Synthetic 3x QQQ proxy"; equityCurve: EquityPoint[]; stats: PerformanceStats } | null;
  events: Array<{ date: string; type: string; symbols: string[]; reason: string }>;
};
export type OosRecord = {
  strategyId: string;
  signalMonth: string;
  signalDate: string;
  executionDate: string | null;
  universeSymbols: string[];
  rankedCandidates: unknown[];
  selectedSymbols: string[];
  targetWeights: number[];
  marketState: string;
  riskState: string;
  entryPrices: Record<string, number>;
  exitPrices: Record<string, number>;
  return: number | null;
  equity: number | null;
  triggerHistory: unknown[];
};
export type ForwardOosResult = {
  strategyId: string;
  startedAt: string;
  asOf: string | null;
  source: "Yahoo Finance adjusted OHLC";
  baselineBacktestEquity: number | null;
  equityCurve: EquityPoint[];
  stats: PerformanceStats;
  records: OosRecord[];
};
export type NportOperations = {
  activeQuarter: string | null;
  lastImportedAt: string | null;
  nextImportDeadlineAt: string;
  universeMode: "CURRENT" | "FALLBACK";
  fallbackReason: string | null;
  extraordinaryRebalance: {
    evaluatedAt: string;
    priceAsOf: string;
    changed: boolean;
    executionDate: string | null;
    previousSymbols: string[];
    previousWeights: number[];
    nextSymbols: string[];
    nextWeights: number[];
    signal: MonthlySignal;
  } | null;
};
export type DashboardPayload = {
  generatedAt: string;
  source: "live" | "snapshot";
  warning?: string;
  config: StrategyConfig;
  currentUniverse: UniverseMonth | null;
  currentSignal: MonthlySignal | null;
  liveState: LiveStrategyState;
  qqq: { close: number | null; monthlyMa: number | null; dailySma: number | null; momentum20d: number | null };
  oos: ForwardOosResult;
  backtest: BacktestResult;
  expectedCagr?: ExpectedCagrModel;
  nportOperations?: NportOperations;
};
