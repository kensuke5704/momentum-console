import type { PortfolioTarget } from "./portfolio-types";
import type { BacktestResult } from "./types";

type Execution = BacktestResult["events"][number];

function allocationKey(targets: PortfolioTarget[]): string {
  const weights = new Map<string, number>();
  for (const { symbol, weight } of targets) {
    weights.set(symbol, (weights.get(symbol) ?? 0) + weight);
  }
  return [...weights].filter(([, weight]) => Math.abs(weight) > 1e-8)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([symbol, weight]) => `${symbol}:${weight.toFixed(8)}`).join("|");
}

/** Display allocation changes only; leave the strategy's execution log untouched. */
export function recentAllocationChanges(events: Execution[], startDate: string, limit = 5): Execution[] {
  const formalReasons = new Map<string, string[]>();
  for (const event of events) {
    if (!["ENTRY_OPEN", "EXIT_OPEN"].includes(event.type) || !event.reason || event.reason === "No pending order") continue;
    const reasons = formalReasons.get(event.date) ?? [];
    if (!reasons.includes(event.reason)) reasons.push(event.reason);
    formalReasons.set(event.date, reasons);
  }
  let previous = allocationKey([{ symbol: "CASH", weight: 1, role: "CASH" }]);
  const changes: Execution[] = [];
  for (const event of [...events].filter((entry) => entry.type === "PORTFOLIO_REBALANCE_OPEN")
    .sort((left, right) => left.date.localeCompare(right.date))) {
    // Older payloads without weights cannot establish an allocation change.
    if (!event.targets) continue;
    const current = allocationKey(event.targets);
    if (current !== previous && event.date >= startDate) {
      const reasons = formalReasons.get(event.date);
      // The wrapper's generic target-change message is not the underlying trigger.
      // Preserve a simultaneous regime change while showing the actual Fixed60 reason.
      const reason = reasons?.length
        ? [...(event.reason.startsWith("Regime changed ") ? [event.reason] : []), ...reasons].join("; ")
        : event.reason;
      changes.push({ ...event, reason });
    }
    previous = current;
  }
  return changes.reverse().slice(0, limit);
}
