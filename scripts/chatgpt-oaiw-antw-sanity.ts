import { TICKERS } from "../src/lib/config";
import { FROZEN_STRATEGY, FROZEN_STRATEGY_ID } from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import { fetchHistories } from "../src/lib/yahoo";
import type { TickerConfig } from "../src/lib/types";

async function main() {
  const candidates: TickerConfig[] = [
    { symbol: "WULF", genre: "AI Infrastructure" },
    { symbol: "HUT", genre: "AI Infrastructure" },
    { symbol: "AMD", genre: "AI Semi" },
    { symbol: "AVGO", genre: "AI Semi" },
    { symbol: "ORCL", genre: "AI Infrastructure" },
    { symbol: "IREN", genre: "AI Infrastructure" },
    { symbol: "CORZ", genre: "AI Infrastructure" },
  ];

  const all = [...TICKERS, ...candidates];
  const histories = await fetchHistories(all.map((x) => x.symbol));
  const baseline = buildDashboard(histories, TICKERS, FROZEN_STRATEGY);
  const base = baseline.metrics;
  const baselineSelections = new Map(baseline.monthly.map((m) => [m.signalMonth, new Set(m.selectedSymbols)]));

  const out = [];
  for (const c of candidates) {
    const universe = [...TICKERS, c];
    const d = buildDashboard(histories, universe, FROZEN_STRATEGY);
    const selectedDetail = d.monthly
      .filter((m) => m.selectedSymbols.includes(c.symbol))
      .map((m) => {
        const baseSel = baselineSelections.get(m.signalMonth) ?? new Set<string>();
        const displaced = [...baseSel].filter((s) => !m.selectedSymbols.includes(s));
        return { signalMonth: m.signalMonth, entryDate: m.entryDate, exitDate: m.exitDate, displaced };
      });
    out.push({
      symbol: c.symbol,
      genre: c.genre,
      selectedMonths: selectedDetail.length,
      changedMonths: selectedDetail.filter((x) => x.displaced.length > 0).length,
      cagr: d.metrics.cagr,
      deltaCagr: d.metrics.cagr - base.cagr,
      maxDrawdown: d.metrics.maxDrawdown,
      deltaMaxDrawdown: d.metrics.maxDrawdown - base.maxDrawdown,
      annualizedVolatility: d.metrics.annualizedVolatility,
      deltaAnnualizedVolatility: d.metrics.annualizedVolatility - base.annualizedVolatility,
      calmar: d.metrics.calmar,
      deltaCalmar: d.metrics.calmar - base.calmar,
      selectedDetail,
    });
  }
  console.log("OAIW_ANTW_SANITY_JSON_START");
  console.log(JSON.stringify({ strategyId: FROZEN_STRATEGY_ID, baseline: base, candidates: out }, null, 2));
  console.log("OAIW_ANTW_SANITY_JSON_END");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
