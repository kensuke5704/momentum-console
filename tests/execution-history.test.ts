import assert from "node:assert/strict";
import test from "node:test";
import { recentAllocationChanges } from "../src/lib/execution-history";
import type { PortfolioTarget } from "../src/lib/portfolio-types";

const targets = (weight: number, symbol = "GLDM"): PortfolioTarget[] => [
  { symbol, weight, role: "DIVERSIFIER" },
  { symbol: "CASH", weight: 1 - weight, role: "CASH" },
];
const event = (date: string, allocation?: PortfolioTarget[]) => ({
  date, type: "PORTFOLIO_REBALANCE_OPEN", symbols: [], reason: "test", targets: allocation,
});

test("unchanged monthly allocations are excluded even with reordered targets or floating-point noise", () => {
  const events = [event("2026-09-02", targets(.225)), event("2026-09-03", targets(.225).reverse()),
    event("2026-09-04", targets(.225 + 1e-12)), event("2026-09-08", targets(.3)),
    event("2026-10-01", targets(.3)), event("2026-10-02", targets(.3, "MU"))];
  assert.deepEqual(recentAllocationChanges(events.reverse(), "2026-09-02").map((entry) => entry.date),
    ["2026-10-02", "2026-09-08", "2026-09-02"]);
});

test("pre-OOS allocation is used for comparison and missing weights are not guessed", () => {
  const events = [event("2026-08-31", targets(.225)), event("2026-09-02", targets(.225)),
    event("2026-09-03"), event("2026-09-04", targets(.225)), event("2026-09-08", targets(.3))];
  assert.deepEqual(recentAllocationChanges(events, "2026-09-02").map((entry) => entry.date), ["2026-09-08"]);
});

test("only the latest five changes are returned, including transitions to cash", () => {
  const events = Array.from({ length: 7 }, (_, index) => event(`2026-09-0${index + 1}`, targets(index % 2 ? 0 : .3)));
  const original = structuredClone(events);
  assert.deepEqual(recentAllocationChanges(events, "2026-09-01").map((entry) => entry.date),
    ["2026-09-07", "2026-09-06", "2026-09-05", "2026-09-04", "2026-09-03"]);
  assert.deepEqual(events, original);
  assert.deepEqual(recentAllocationChanges([event("2026-09-01", targets(0))], "2026-09-01"), []);
});

test("history shows the formal recovery or circuit reason without mutating events", () => {
  const events = [
    { ...event("2026-09-03", targets(.225)), reason: "Initial frozen Stage21 allocation" },
    { ...event("2026-09-03"), type: "EXIT_OPEN", reason: "Portfolio close breached -15% circuit" },
    { ...event("2026-10-01", targets(.3, "MU")), reason: "Fixed60 funded target changed" },
    { ...event("2026-10-01"), type: "ENTRY_OPEN", reason: "10 recovery closes confirmed" },
  ];
  const original = structuredClone(events);
  assert.deepEqual(recentAllocationChanges(events, "2026-09-02").map((entry) => entry.reason),
    ["10 recovery closes confirmed", "Portfolio close breached -15% circuit"]);
  assert.deepEqual(events, original);
});

test("simultaneous regime and Fixed60 reasons are retained; placeholder reasons are ignored", () => {
  const events = [
    { ...event("2026-09-08", targets(.3)), reason: "Regime changed YELLOW -> DEEP" },
    { ...event("2026-09-08"), type: "ENTRY_OPEN", reason: "No pending order" },
    { ...event("2026-10-01", targets(.4)), reason: "Regime changed DEEP -> NORMAL" },
    { ...event("2026-10-01"), type: "ENTRY_OPEN", reason: "10 recovery closes confirmed" },
  ];
  assert.deepEqual(recentAllocationChanges(events, "2026-09-02").map((entry) => entry.reason),
    ["Regime changed DEEP -> NORMAL; 10 recovery closes confirmed", "Regime changed YELLOW -> DEEP"]);
});
