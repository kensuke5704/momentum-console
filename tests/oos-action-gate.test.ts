import assert from "node:assert/strict";
import test from "node:test";
import { evaluateOosActionGate } from "../src/lib/oos-action-gate";
import type { ForwardOosResult } from "../src/lib/types";

function sample(overrides:Partial<ForwardOosResult>={}):ForwardOosResult{return{strategyId:"momentum-stage21-sbi-2026-09-v1",startedAt:"2026-09-02",asOf:"2026-10-02",source:"Yahoo Finance adjusted OHLC",baselineBacktestEquity:1,equityCurve:[{date:"2026-09-02",equity:1,drawdown:0}],stats:{cagr:.3,maxDrawdown:-.1,annualizedVolatility:.2,calmar:3,finalEquity:1.02},records:[],...overrides}}

test("Stage21 warmup stays green while drawdown is contained",()=>assert.equal(evaluateOosActionGate(sample()).level,"GREEN"));
test("Stage21 turns amber at its 17% historical DD review boundary",()=>assert.equal(evaluateOosActionGate(sample({stats:{cagr:.3,maxDrawdown:-.17,annualizedVolatility:.2,calmar:1.7,finalEquity:.9}})).level,"AMBER"));
test("Stage21 turns red at the 25% kill boundary",()=>{const g=evaluateOosActionGate(sample({stats:{cagr:-.3,maxDrawdown:-.25,annualizedVolatility:.5,calmar:-1.2,finalEquity:.7}}));assert.equal(g.level,"RED");assert.equal(g.blocksNewEntries,true)});
test("Stage21 turns red after 12 months when CAGR is negative and DD breaches 17%",()=>assert.equal(evaluateOosActionGate(sample({asOf:"2027-09-03",stats:{cagr:-.01,maxDrawdown:-.18,annualizedVolatility:.3,calmar:-.05,finalEquity:.98}})).level,"RED"));
test("Stage21 turns red after 24 months below 15% gross CAGR",()=>assert.equal(evaluateOosActionGate(sample({asOf:"2028-09-03",stats:{cagr:.14,maxDrawdown:-.1,annualizedVolatility:.2,calmar:1.4,finalEquity:1.3}})).level,"RED"));
test("Stage21 stays green after 24 months above the preregistered hurdle",()=>assert.equal(evaluateOosActionGate(sample({asOf:"2028-09-03",stats:{cagr:.30,maxDrawdown:-.1,annualizedVolatility:.2,calmar:3,finalEquity:1.7}})).level,"GREEN"));
