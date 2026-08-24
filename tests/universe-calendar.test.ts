import assert from "node:assert/strict";
import test from "node:test";
import { isCompletedSignalMonth } from "../src/lib/universe/universe";

test("current partial calendar month is not a completed monthly signal", () => {
  const current = "2026-08";
  const marketMonths = ["2026-06", "2026-07", "2026-08"];
  assert.deepEqual(marketMonths.filter((month) => isCompletedSignalMonth(month, current)), ["2026-06", "2026-07"]);
});
