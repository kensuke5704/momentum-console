import { describe, expect, it } from "vitest";
import { evaluateOosActionGate } from "@/lib/oos-action-gate";
import type { ForwardOosResult } from "@/lib/types";

function sample(overrides: Partial<ForwardOosResult> = {}): ForwardOosResult {
  return {
    strategyId: "momentum-fixed60-2026-08-v1",
    startedAt: "2026-08-31",
    asOf: "2026-09-30",
    source: "Yahoo Finance adjusted OHLC",
    baselineBacktestEquity: 1,
    equityCurve: [{ date: "2026-08-31", equity: 1, drawdown: 0 }],
    stats: { cagr: 0.3, maxDrawdown: -0.1, annualizedVolatility: 0.2, calmar: 3, finalEquity: 1.02 },
    records: [],
    ...overrides,
  };
}

describe("evaluateOosActionGate", () => {
  it("keeps warmup green when drawdown is contained", () => {
    const gate = evaluateOosActionGate(sample());
    expect(gate.level).toBe("GREEN");
    expect(gate.blocksNewEntries).toBe(false);
  });

  it("turns amber at -30% max drawdown", () => {
    const gate = evaluateOosActionGate(sample({ stats: { cagr: 0.3, maxDrawdown: -0.30, annualizedVolatility: 0.2, calmar: 1, finalEquity: 0.8 } }));
    expect(gate.level).toBe("AMBER");
  });

  it("turns red at -40% max drawdown regardless of horizon", () => {
    const gate = evaluateOosActionGate(sample({ stats: { cagr: -0.5, maxDrawdown: -0.40, annualizedVolatility: 0.5, calmar: -1, finalEquity: 0.6 } }));
    expect(gate.level).toBe("RED");
    expect(gate.blocksNewEntries).toBe(true);
  });

  it("turns red after 12 months when CAGR is negative and max drawdown exceeds 30%", () => {
    const gate = evaluateOosActionGate(sample({
      asOf: "2027-09-01",
      stats: { cagr: -0.01, maxDrawdown: -0.31, annualizedVolatility: 0.3, calmar: -0.03, finalEquity: 0.98 },
    }));
    expect(gate.level).toBe("RED");
  });

  it("turns red at 24 months if gross CAGR is already below the after-tax 20% hurdle", () => {
    const gate = evaluateOosActionGate(sample({
      asOf: "2028-09-01",
      stats: { cagr: 0.19, maxDrawdown: -0.2, annualizedVolatility: 0.3, calmar: 0.95, finalEquity: 1.4 },
    }));
    expect(gate.level).toBe("RED");
  });

  it("uses amber after 24 months while exact after-tax CAGR is unavailable", () => {
    const gate = evaluateOosActionGate(sample({
      asOf: "2028-09-01",
      stats: { cagr: 0.35, maxDrawdown: -0.2, annualizedVolatility: 0.3, calmar: 1.75, finalEquity: 1.8 },
    }));
    expect(gate.level).toBe("AMBER");
  });
});
