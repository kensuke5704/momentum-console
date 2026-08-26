import test from "node:test";
import assert from "node:assert/strict";
import { validateLiveNportSnapshot, type LiveNportSnapshot } from "../src/lib/universe/live-ingestion";

function snapshot(overrides: Partial<LiveNportSnapshot> = {}): LiveNportSnapshot {
  return {
    generatedAt: "2026-08-26T00:00:00.000Z",
    source: "SEC EDGAR",
    baselineMaxFilingDate: "2026-06-30",
    scanStart: "2026-08-01",
    scanEnd: "2026-08-25",
    indexedDays: 17,
    discovered: 3,
    parsedNew: 3,
    parseFailed: 0,
    unresolvedAccessions: [],
    filings: [],
    ...overrides,
  };
}

test("live ingestion fails closed when no SEC daily index was available", () => {
  assert.throws(() => validateLiveNportSnapshot(snapshot({ indexedDays: 0 })), /not available/);
});

test("live ingestion fails closed when no NPORT-P filing was discovered", () => {
  assert.throws(() => validateLiveNportSnapshot(snapshot({ discovered: 0, parsedNew: 0 })), /No NPORT-P filings/);
});

test("live ingestion fails closed on parse failure or unresolved accession", () => {
  assert.throws(() => validateLiveNportSnapshot(snapshot({ parseFailed: 1 })), /parsing is incomplete/);
  assert.throws(() => validateLiveNportSnapshot(snapshot({ unresolvedAccessions: ["0000000000-26-000001"] })), /unresolved/);
});

test("legacy live snapshot without validation metadata is rejected", () => {
  const legacy = { ...snapshot(), indexedDays: undefined, unresolvedAccessions: undefined } as unknown as LiveNportSnapshot;
  assert.throws(() => validateLiveNportSnapshot(legacy), /not available|metadata is incomplete/);
});

test("live ingestion rejects a snapshot that does not reach the required date", () => {
  assert.throws(() => validateLiveNportSnapshot(snapshot(), { expectedScanEnd: "2026-08-26" }), /before required/);
});

test("complete live ingestion snapshot is accepted", () => {
  assert.doesNotThrow(() => validateLiveNportSnapshot(snapshot(), { expectedScanEnd: "2026-08-25" }));
});
