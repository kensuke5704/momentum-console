import assert from "node:assert/strict";
import test from "node:test";
import { buildDashboardPayload } from "../src/lib/dashboard";
import type { CftcPositionRow } from "../src/lib/cftc";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

const universe: UniverseMonth = {
  signalMonth: "2026-08", asOf: "2026-08-31",
  symbols: [
    { symbol: "AAA", universeRank: 1, etfCount: 2, aggregateWeight: 5, maxWeight: 3, recencyWeight: 1, universeScore: 1 },
    { symbol: "BBB", universeRank: 2, etfCount: 2, aggregateWeight: 4, maxWeight: 2, recencyWeight: 1, universeScore: 0.9 },
  ], sourceFilings: [], added: [], removed: [],
};
const point=(date:string,close:number):PricePoint=>({date,open:close,close});
const cftc:CftcPositionRow[]=["2026-07-21","2026-07-28","2026-08-04","2026-08-11","2026-08-18","2026-08-25"].map((reportDate,index)=>({reportDate,net:100-index}));

test("dashboard does not publish a month-end signal before the signal-date QQQ close is activated",()=>{
 const qqq=[point("2026-08-27",99),point("2026-08-28",100)],gldm=[point("2026-08-27",50),point("2026-08-28",50.2)];
 const dashboard=buildDashboardPayload({QQQ:qqq,GLDM:gldm},[universe],cftc);
 assert.equal(dashboard.currentSignal,null);
 assert.equal(dashboard.liveState.pendingSignal,null);
 assert.equal(dashboard.portfolioConfig.strategyId,"momentum-stage21-sbi-2026-09-v1");
});

test("dashboard publishes the Fixed60 signal only once the exact signal-date close exists",()=>{
 const qqq=[point("2026-08-28",100),point("2026-08-31",101)],gldm=[point("2026-08-28",50),point("2026-08-31",50.3)];
 const dashboard=buildDashboardPayload({QQQ:qqq,GLDM:gldm},[universe],cftc);
 assert.equal(dashboard.currentSignal?.signalDate,"2026-08-31");
 assert.equal(dashboard.liveState.pendingSignal?.signalDate,"2026-08-31");
});

test("Stage21 uses a CFTC report as soon as it is PIT-eligible at the portfolio close",()=>{
 const qqq=[point("2026-08-28",100),point("2026-08-31",101),point("2026-09-01",102)];
 const gldm=[point("2026-08-28",50),point("2026-08-31",50.3),point("2026-09-01",50.4)];
 const dashboard=buildDashboardPayload({QQQ:qqq,GLDM:gldm},[universe],cftc);
 assert.equal(dashboard.portfolioState.asOf,"2026-09-01");
 assert.equal(dashboard.portfolioState.cftc.reportDate,"2026-08-25");
});
