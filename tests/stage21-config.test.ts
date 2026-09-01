import assert from "node:assert/strict";
import test from "node:test";
import {cftcStatus,type CftcPositionRow} from "../src/lib/cftc";
import {PRODUCTION_PORTFOLIO} from "../src/lib/portfolio-config";

test("Stage21 funded weights sum to 100% without leverage",()=>{for(const[state,w]of Object.entries(PRODUCTION_PORTFOLIO.weights)){assert.ok(Math.abs(w.fixed60+w.gldm+w.cash-1)<1e-12,state);assert.ok(w.fixed60+w.gldm<=1,state);assert.ok(w.cash>=0,state)}});
test("Stage21 production and legacy inner IDs are separate",()=>assert.notEqual(PRODUCTION_PORTFOLIO.strategyId,PRODUCTION_PORTFOLIO.legacyInnerStrategyId));
test("CFTC Yellow uses four-report deterioration",()=>{const rows:CftcPositionRow[]=[100,110,105,108,90].map((net,i)=>({reportDate:`2026-07-${String(7+i*7).padStart(2,"0")}`,net}));const status=cftcStatus(rows,"2026-08-11");assert.equal(status.yellow,true)});
test("2025 shutdown report is unavailable before its actual release",()=>{const rows:CftcPositionRow[]=[{reportDate:"2025-09-02",net:100},{reportDate:"2025-09-09",net:100},{reportDate:"2025-09-16",net:100},{reportDate:"2025-09-23",net:100},{reportDate:"2025-09-30",net:1}];const before=cftcStatus(rows,"2025-10-20"),after=cftcStatus(rows,"2025-11-26");assert.notEqual(before.reportDate,"2025-09-30");assert.equal(after.reportDate,"2025-09-30")});
