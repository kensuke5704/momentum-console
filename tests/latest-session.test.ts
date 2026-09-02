import assert from "node:assert/strict";
import test from "node:test";
import { latestCompletedUsTradingSession } from "../src/lib/latest-session";

test("latest completed session stays on the prior close before the validation cutoff", () => {
  assert.equal(latestCompletedUsTradingSession(new Date("2026-09-02T20:14:00Z")), "2026-09-01");
});

test("latest completed session advances after the regular-close validation cutoff", () => {
  assert.equal(latestCompletedUsTradingSession(new Date("2026-09-02T20:15:00Z")), "2026-09-02");
});

test("latest completed session skips weekends and US market holidays", () => {
  assert.equal(latestCompletedUsTradingSession(new Date("2026-09-06T16:00:00Z")), "2026-09-04");
  assert.equal(latestCompletedUsTradingSession(new Date("2026-09-07T20:30:00Z")), "2026-09-04");
});
