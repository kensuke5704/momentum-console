export type MarketState = "RiskOn" | "Cash" | "Unknown";
export type AllocationStatus = "Invest" | "CashMarket" | "CashInsufficient";

export type PricePoint = {
  date: string;
  close: number;
};

export type TickerConfig = {
  symbol: string;
  genre: string;
};

export type StrategyConfig = {
  topN: number;
  weights: {
    oneMonth: number;
    threeMonth: number;
    sixMonth: number;
  };
  surgeLimit: number;
  qqqMaMonths: number;
  frontierMax: number;
  genreLimits: Record<string, number>;
  frontierGenres: string[];
  excludedTickers: string[];
  backtestStart: string;
  targetTotalJpy: number;
  usdJpy: number;
};

export type MomentumRow = {
  symbol: string;
  genre: string;
  current: number | null;
  oneMonth: number | null;
  threeMonth: number | null;
  sixMonth: number | null;
  score: number | null;
  rank: number | null;
  eligible: boolean;
  selected: boolean;
  reason: string;
};

export type PortfolioRow = MomentumRow & {
  targetAmount: number;
  targetShares: number | null;
};

export type BacktestRow = {
  signalMonth: string;
  entryDate: string | null;
  exitDate: string | null;
  market: MarketState | "Not enough candidates";
  picks: string[];
  monthlyReturn: number | null;
  equity: number | null;
  provisional?: boolean;
};

export type BacktestStats = {
  finalEquity: number;
  cagr: number;
  averageMonthlyReturn: number;
  monthlyVolatility: number;
  annualizedVolatility: number;
  maxDrawdown: number;
};

export type DashboardPayload = {
  source: "live" | "snapshot";
  asOf: string;
  warning?: string;
  market: {
    state: MarketState;
    decisionDate: string;
    qqq: number | null;
    ma10: number | null;
    qqqScore: number | null;
    allocationStatus: AllocationStatus;
    selectedCount: number;
  };
  momentum: MomentumRow[];
  portfolio: PortfolioRow[];
  backtest: {
    rows: BacktestRow[];
    stats: BacktestStats;
  };
  config: StrategyConfig;
};
