import assert from "node:assert/strict";
import test from "node:test";
import { nextUsTradingSession } from "../src/lib/trading-calendar";

test("returns the next weekday when it is a regular US trading session", () => {
  assert.equal(nextUsTradingSession("2026-08-25"), "2026-08-26");
});

test("skips weekends", () => {
  assert.equal(nextUsTradingSession("2026-08-28"), "2026-08-31");
});

test("skips observed Independence Day", () => {
  assert.equal(nextUsTradingSession("2026-07-02"), "2026-07-06");
});

test("skips Christmas and the following weekend", () => {
  assert.equal(nextUsTradingSession("2026-12-24"), "2026-12-28");
});

test("skips Good Friday", () => {
  assert.equal(nextUsTradingSession("2026-04-02"), "2026-04-06");
});
