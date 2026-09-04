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

test("Stage21 carries the last confirmed close across an isolated held-asset data gap",()=>{
 const qqq=[point("2026-08-27",100),point("2026-08-28",100),point("2026-08-31",100),point("2026-09-01",100)];
 const gldm=[point("2026-08-27",50),point("2026-08-28",50),point("2026-09-01",50)];
 const dashboard=buildDashboardPayload({QQQ:qqq,GLDM:gldm},[universe],cftc);
 const curve=dashboard.backtest.equityCurve;
 const dailyReturns=curve.slice(1).map((row,index)=>row.equity/curve[index].equity-1);
 assert.ok(Math.min(...dailyReturns)>-0.01);
});

test("OOS keeps the current daily simulation when the displayed backtest is frozen",()=>{
 const qqq=[point("2026-08-28",100),point("2026-08-31",101),point("2026-09-01",102),point("2026-09-02",103)],gldm=[point("2026-08-28",50),point("2026-08-31",50.3),point("2026-09-01",50.4),point("2026-09-02",50.5)];
 const live=buildDashboardPayload({QQQ:qqq,GLDM:gldm},[universe],cftc);
 const frozen={...live.backtest,equityCurve:live.backtest.equityCurve.slice(0,1)};
 const dashboard=buildDashboardPayload({QQQ:qqq,GLDM:gldm},[universe],cftc,"live",{frozenBacktest:frozen});
 assert.equal(dashboard.backtest.equityCurve.length,1);
 assert.ok(dashboard.oosBacktest.equityCurve.length>dashboard.backtest.equityCurve.length);
 assert.equal(dashboard.portfolioState.nextAction.type,"REBALANCE_NEXT_OPEN");
 assert.equal(dashboard.portfolioState.nextAction.executionDate,"2026-09-03");
 assert.equal(dashboard.portfolioState.nextAction.reason,"Initial frozen Stage21 allocation");
});

test("Stage21 keeps its GLDM/Cash sleeve when the shared Fixed60 circuit exits",()=>{
 const dates=Array.from({length:364},(_,index)=>new Date(Date.UTC(2025,0,1+index)).toISOString().slice(0,10));
 const qqq=dates.map((date,index)=>point(date,index<=360?100+index*.05:80));
 const aaa=dates.map((date,index)=>point(date,index===362?(100+361*.15)*.84:100+index*.15));
 const bbb=dates.map((date,index)=>point(date,index===362?(90+361*.12)*.84:90+index*.12));
 const gldm=dates.map(date=>point(date,50));
 const circuitUniverse:UniverseMonth={...universe,signalMonth:dates[360].slice(0,7),asOf:dates[360]};
 const dashboard=buildDashboardPayload({QQQ:qqq,AAA:aaa,BBB:bbb,GLDM:gldm},[circuitUniverse],[]);
 assert.match(dashboard.liveState.lastTrigger??"",/circuit/);
 assert.deepEqual(dashboard.portfolioState.targets.map(target=>target.symbol),["GLDM","CASH"]);
 assert.ok(dashboard.oosBacktest.events.some(event=>event.type==="EXIT_OPEN"&&event.reason.includes("circuit")));
});
