import assert from "node:assert/strict";
import test from "node:test";
import { buildDashboardPayload } from "../src/lib/dashboard";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

const universe: UniverseMonth = {
  signalMonth: "2026-08",
  asOf: "2026-08-31",
  symbols: [
    { symbol: "AAA", universeRank: 1, etfCount: 2, aggregateWeight: 5, maxWeight: 3, recencyWeight: 1, universeScore: 1 },
    { symbol: "BBB", universeRank: 2, etfCount: 2, aggregateWeight: 4, maxWeight: 2, recencyWeight: 1, universeScore: 0.9 },
  ],
  sourceFilings: [],
  added: [],
  removed: [],
};

const point = (date: string, close: number): PricePoint => ({ date, open: close, close });

test("dashboard does not publish a month-end signal before the signal-date QQQ close is activated", () => {
  const dashboard = buildDashboardPayload({ QQQ: [point("2026-08-28", 100)] }, [universe]);
  assert.equal(dashboard.currentSignal, null);
  assert.equal(dashboard.liveState.pendingSignal, null);
});

test("dashboard publishes the signal only once the exact signal-date close exists", () => {
  const dashboard = buildDashboardPayload({ QQQ: [point("2026-08-28", 100), point("2026-08-31", 101)] }, [universe]);
  assert.equal(dashboard.currentSignal?.signalDate, "2026-08-31");
  assert.equal(dashboard.liveState.pendingSignal?.signalDate, "2026-08-31");
});
