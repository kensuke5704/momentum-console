import assert from "node:assert/strict";
import test from "node:test";
import { PRODUCTION_PORTFOLIO } from "../src/lib/portfolio-config";
import { emptyForwardOos, OOS_START_DATE, updateForwardOos } from "../src/lib/oos";
import type { BacktestResult, EquityPoint } from "../src/lib/types";

const backtest=(equityCurve:EquityPoint[]):BacktestResult=>({strategyId:PRODUCTION_PORTFOLIO.strategyId,equityCurve,stats:{cagr:0,maxDrawdown:0,annualizedVolatility:0,calmar:null,finalEquity:equityCurve.at(-1)?.equity??1},benchmark:null,events:[]});

test("Forward OOS starts on the Stage21 frozen production date",()=>{const empty=emptyForwardOos(PRODUCTION_PORTFOLIO.strategyId);assert.equal(empty.startedAt,OOS_START_DATE);assert.equal(OOS_START_DATE,"2026-09-02");assert.deepEqual(empty.equityCurve,[{date:OOS_START_DATE,equity:1,drawdown:0}])});

test("Forward OOS uses actual post-start equity and appends without rewriting confirmed dates",()=>{const first=updateForwardOos(backtest([{date:"2026-09-01",equity:18,drawdown:0},{date:"2026-09-02",equity:20,drawdown:0},{date:"2026-09-03",equity:22,drawdown:0}]));assert.equal(first.baselineBacktestEquity,20);assert.deepEqual(first.equityCurve.map(p=>[p.date,p.equity]),[["2026-09-02",1],["2026-09-03",1.1]]);const appended=updateForwardOos(backtest([{date:"2026-09-02",equity:20,drawdown:0},{date:"2026-09-03",equity:99,drawdown:0},{date:"2026-09-04",equity:24,drawdown:0}]),first);assert.equal(appended.equityCurve.find(p=>p.date==="2026-09-03")?.equity,1.1);assert.equal(appended.equityCurve.find(p=>p.date==="2026-09-04")?.equity,1.2);assert.equal(appended.asOf,"2026-09-04")});

test("legacy Fixed60 OOS is not carried into Stage21",()=>{const stale={...emptyForwardOos("momentum-fixed60-2026-08-v1"),startedAt:"2026-08-31"};const updated=updateForwardOos(backtest([{date:"2026-09-02",equity:20,drawdown:0}]),stale);assert.equal(updated.strategyId,PRODUCTION_PORTFOLIO.strategyId);assert.equal(updated.startedAt,OOS_START_DATE);assert.deepEqual(updated.records,[])});

test("validated fallback OOS is replaceable when completed adjusted row arrives",()=>{const provisional=updateForwardOos(backtest([{date:"2026-09-02",equity:20,drawdown:0},{date:"2026-09-03",equity:22,drawdown:0}]),null,["2026-09-03"]);assert.deepEqual(provisional.provisionalDates,["2026-09-03"]);assert.equal(provisional.equityCurve.at(-1)?.equity,1.1);const confirmed=updateForwardOos(backtest([{date:"2026-09-02",equity:20,drawdown:0},{date:"2026-09-03",equity:21,drawdown:0}]),provisional);assert.deepEqual(confirmed.provisionalDates,[]);assert.equal(confirmed.equityCurve.at(-1)?.equity,1.05)});
