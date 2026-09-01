export type PortfolioRegime = "NORMAL"|"YELLOW"|"DEEP";
export type PortfolioTarget = { symbol:string; weight:number; role:"FIXED60"|"DIVERSIFIER"|"CASH" };
export type PortfolioNextAction = {
  type:"REBALANCE_NEXT_OPEN"|"HOLD";
  executionDate:string|null;
  targets:PortfolioTarget[];
  reason:string;
};
export type PortfolioLiveState = {
  strategyId:string;
  asOf:string;
  regime:PortfolioRegime;
  cftc:{ reportDate:string|null; net:number|null; priorNet:number|null; yellow:boolean };
  m3:{ deep:boolean; coreReturn20:number|null; qqqReturn20:number|null; gap:number|null; recoveryConfirm:number };
  fixed60:{ strategyId:string; riskState:string; symbols:string[]; innerWeights:number[] };
  targets:PortfolioTarget[];
  nextAction:PortfolioNextAction;
};
export type PortfolioConfigView = {
  strategyId:string;
  legacyInnerStrategyId:string;
  oosStartDate:string;
  weights:Record<PortfolioRegime,{fixed60:number;gldm:number;cash:number}>;
  execution:{rebalance:string;transactionCost:number;monthlyRebalance:boolean;wholeSharesAtBroker:boolean};
  researchReference:{releaseAwareHistoricalCagr:number;historicalMaxDrawdown:number;planningCagrProxy:number;rolling36MedianCagr:number;rolling36P10Cagr:number;rolling36WorstCagr:number;note:string};
};
