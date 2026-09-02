import assert from "node:assert/strict";
import test from "node:test";
import frozen from "../public/data/backtest-frozen.json";
import { PRODUCTION_PORTFOLIO } from "../src/lib/portfolio-config";

test("the displayed Stage21 backtest is frozen at the OOS boundary",()=>{
 assert.equal(frozen.strategyId,PRODUCTION_PORTFOLIO.strategyId);
 assert.equal(frozen.backtest.strategyId,PRODUCTION_PORTFOLIO.strategyId);
 assert.equal(frozen.frozenAt,PRODUCTION_PORTFOLIO.oosStartDate);
 assert.equal(frozen.dataThrough,"2026-09-01");
 assert.equal(frozen.backtest.equityCurve.at(-1)?.date,frozen.dataThrough);
});
