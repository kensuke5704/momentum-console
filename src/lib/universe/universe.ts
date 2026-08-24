import { PRODUCTION_STRATEGY } from "../config";
import type { NportFiling, UniverseMember, UniverseMonth } from "../types";
import { latestPublicFilings } from "./sec-nport";

const DAY_MS = 86_400_000;
const ageDays = (asOf: string, filed: string) => Math.max(0, (Date.parse(`${asOf}T00:00:00Z`) - Date.parse(`${filed}T00:00:00Z`)) / DAY_MS);

export function isCompletedSignalMonth(month: string, currentCalendarMonth = new Date().toISOString().slice(0, 7)): boolean {
  return month < currentCalendarMonth;
}

export function buildPointInTimeUniverse(filings: NportFiling[], signalMonth: string, asOf: string, previous?: UniverseMonth | null, size = PRODUCTION_STRATEGY.universe.size): UniverseMonth {
  const sources = latestPublicFilings(filings, asOf);
  const rows = new Map<string, { seriesIds: Set<string>; aggregateWeight: number; maxWeight: number; recencyWeight: number }>();
  for (const filing of sources) {
    const recencyFactor = Math.exp(-ageDays(asOf, filing.filingDate) / 120);
    for (const holding of filing.holdings) {
      if (!(holding.weight > 0)) continue;
      const symbol = holding.symbol.trim().toUpperCase();
      if (!symbol) continue;
      const row = rows.get(symbol) ?? { seriesIds: new Set<string>(), aggregateWeight: 0, maxWeight: 0, recencyWeight: 0 };
      row.seriesIds.add(filing.seriesId);
      row.aggregateWeight += holding.weight;
      row.maxWeight = Math.max(row.maxWeight, holding.weight);
      row.recencyWeight += holding.weight * recencyFactor;
      rows.set(symbol, row);
    }
  }
  const symbols: UniverseMember[] = [...rows.entries()].map(([symbol, row]) => {
    const etfCount = row.seriesIds.size;
    return { symbol, universeRank: 0, etfCount, aggregateWeight: row.aggregateWeight, maxWeight: row.maxWeight, recencyWeight: row.recencyWeight, universeScore: 3 * Math.log1p(etfCount) + 0.5 * Math.log1p(row.aggregateWeight) + 0.5 * Math.log1p(row.recencyWeight) };
  }).filter((row) => row.etfCount >= 2 || row.maxWeight >= 4)
    .sort((a, b) => b.universeScore - a.universeScore || b.etfCount - a.etfCount || b.aggregateWeight - a.aggregateWeight || a.symbol.localeCompare(b.symbol))
    .slice(0, Math.max(0, size)).map((row, index) => ({ ...row, universeRank: index + 1 }));
  const prior = new Set(previous?.symbols.map((row) => row.symbol) ?? []);
  const current = new Set(symbols.map((row) => row.symbol));
  return { signalMonth, asOf, symbols, sourceFilings: sources.map(({ accession, seriesId, seriesName, filingDate }) => ({ accession, seriesId, seriesName, filingDate })), added: symbols.map((row) => row.symbol).filter((symbol) => !prior.has(symbol)), removed: previous ? previous.symbols.map((row) => row.symbol).filter((symbol) => !current.has(symbol)) : [] };
}
