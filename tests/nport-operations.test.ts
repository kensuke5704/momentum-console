import assert from "node:assert/strict";
import test from "node:test";
import { buildDelayedNportRebalance, fallbackUniverse, nextNportImportDeadline, requiresUniverseFallback } from "../src/lib/nport-operations";
import { restoreFileSet, snapshotFileSet } from "../src/lib/file-transaction";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

const points = (growth: number, interim?: number): PricePoint[] => {
  const rows = Array.from({ length: 12 }, (_, index) => ({ date: `2025-${String(index + 1).padStart(2, "0")}-28`, open: 100 + growth * index, close: 100 + growth * index }));
  if (interim) rows.push({ date: "2026-01-08", open: interim, close: interim });
  return rows;
};
const qqq = points(1);
const universe = (symbols: string[]): UniverseMonth => ({ signalMonth: "2025-12", asOf: "2025-12-28", symbols: symbols.map((symbol, index) => ({ symbol, universeRank: index + 1, etfCount: 2, aggregateWeight: 10, maxWeight: 5, recencyWeight: 9, universeScore: 10 - index })), sourceFilings: [], added: [], removed: [] });
const histories = { QQQ: qqq, AAA: points(12), BBB: points(9), CCC: points(7), DDD: points(5) };

test("an imported quarterly Universe is used before the month-open signal", () => {
  assert.equal(requiresUniverseFallback("2025-12", "2025q4"), false);
});

test("N-PORT deadline targets the first US trading day of the next required quarter update month", () => {
  assert.equal(nextNportImportDeadline("2026q1"), "2026-07-01T09:00:00+09:00");
  assert.equal(nextNportImportDeadline("2026q2"), "2026-10-01T09:00:00+09:00");
  assert.equal(nextNportImportDeadline("2026q3"), "2027-01-04T09:00:00+09:00");
  assert.equal(nextNportImportDeadline("2026q4"), "2027-04-01T09:00:00+09:00");
});

test("N-PORT deadline skips a weekend at the start of the update month", () => {
  assert.equal(nextNportImportDeadline("2022q2"), "2022-10-03T09:00:00+09:00");
});

test("missing quarterly ZIP retains the previous valid Universe as fallback", () => {
  const old = universe(["AAA", "BBB"]);
  const fallback = fallbackUniverse(old, "2026-03", "2026-03-31");
  assert.deepEqual(fallback.symbols, old.symbols);
  assert.equal(requiresUniverseFallback("2026-03", "2025q4"), true);
});

test("delayed ZIP schedules an extraordinary next-open rebalance when Top2 changes", () => {
  const previous = buildMonthlySignal({ universe: universe(["AAA", "DDD"]), histories, qqq, nextSessionDate: "2026-01-02" });
  const decision = buildDelayedNportRebalance({ previousSignal: previous, newUniverse: universe(["BBB", "CCC"]), histories, qqq, receivedAt: "2026-01-08T08:00:00Z" });
  assert.equal(decision.changed, true);
  assert.equal(decision.executionDate, "2026-01-09");
});

test("delayed ZIP causes no trade when Top2 and target weights are unchanged", () => {
  const previous = buildMonthlySignal({ universe: universe(["AAA", "BBB"]), histories, qqq, nextSessionDate: "2026-01-02" });
  const decision = buildDelayedNportRebalance({ previousSignal: previous, newUniverse: universe(["AAA", "BBB", "DDD"]), histories, qqq, receivedAt: "2026-01-08T08:00:00Z" });
  assert.equal(decision.changed, false);
  assert.equal(decision.executionDate, null);
});

test("delayed selection ignores receipt-day and interim-month prices", () => {
  const previous = buildMonthlySignal({ universe: universe(["AAA", "DDD"]), histories, qqq, nextSessionDate: "2026-01-02" });
  const withInterim = { ...histories, BBB: points(9, 10_000), CCC: points(7, 1) };
  const baseline = buildDelayedNportRebalance({ previousSignal: previous, newUniverse: universe(["BBB", "CCC"]), histories, qqq, receivedAt: "2026-01-08T08:00:00Z" });
  const delayed = buildDelayedNportRebalance({ previousSignal: previous, newUniverse: universe(["BBB", "CCC"]), histories: withInterim, qqq: [...qqq, { date: "2026-01-08", open: 1, close: 1 }], receivedAt: "2026-01-08T08:00:00Z" });
  assert.deepEqual(delayed.signal.selectedSymbols, baseline.signal.selectedSymbols);
  assert.deepEqual(delayed.signal.targetWeights, baseline.signal.targetWeights);
  assert.equal(delayed.priceAsOf, "2025-12-28");
});

test("a mismatched delayed activation fails closed before replacing the active signal", () => {
  const previous = buildMonthlySignal({ universe: universe(["AAA", "BBB"]), histories, qqq, nextSessionDate: "2026-01-02" });
  const broken = { ...universe(["AAA", "BBB"]), signalMonth: "2026-01", asOf: "2026-01-30" };
  assert.throws(() => buildDelayedNportRebalance({ previousSignal: previous, newUniverse: broken, histories, qqq, receivedAt: "2026-01-08T08:00:00Z" }), /official month-end/);
});

test("failed activation restores old artifacts and removes partial new files", async () => {
  const root = await mkdtemp(join(tmpdir(), "nport-transaction-"));
  const oldPath = join(root, "active.json"), partialPath = join(root, "partial.json");
  await writeFile(oldPath, "old");
  const snapshot = await snapshotFileSet([oldPath, partialPath]);
  await writeFile(oldPath, "broken");
  await writeFile(partialPath, "partial");
  await restoreFileSet(snapshot);
  assert.equal(await readFile(oldPath, "utf8"), "old");
  await assert.rejects(readFile(partialPath), /ENOENT/);
});
