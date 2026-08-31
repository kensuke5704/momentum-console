import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { evaluateOosActionGate } from "../src/lib/oos-action-gate";
import type { ForwardOosResult } from "../src/lib/types";

const file = resolve(process.cwd(), process.argv[2] ?? "public/data/oos-performance.json");
const oos = JSON.parse(readFileSync(file, "utf8")) as ForwardOosResult;
const gate = evaluateOosActionGate(oos);

const report = {
  strategyId: oos.strategyId,
  startedAt: oos.startedAt,
  asOf: oos.asOf,
  phase: gate.phase,
  monthsObserved: gate.monthsObserved,
  actionGate: gate.level,
  instruction: gate.instruction,
  reason: gate.reason,
  gross: {
    cagr: oos.asOf ? oos.stats.cagr : null,
    maxDrawdown: oos.asOf ? oos.stats.maxDrawdown : null,
    annualizedVolatility: oos.asOf ? oos.stats.annualizedVolatility : null,
    finalEquity: oos.asOf ? oos.stats.finalEquity : null,
  },
  observations: Math.max(0, oos.equityCurve.length - 1),
  provisionalDates: oos.provisionalDates ?? [],
  interpretation:
    gate.monthsObserved < 3
      ? "IMPLEMENTATION_ONLY_NO_CAGR_INFERENCE"
      : gate.monthsObserved < 12
        ? "DESCRIPTIVE_ONLY"
        : gate.monthsObserved < 24
          ? "FIRST_PERFORMANCE_CHECKPOINT"
          : gate.monthsObserved < 36
            ? "TAX_AWARE_CHECKPOINT_REQUIRES_EXACT_AFTER_TAX_SERIES"
            : "STRATEGY_OBJECTIVE_CHECKPOINT",
};

process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
