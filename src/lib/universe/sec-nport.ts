import type { NportFiling } from "../types";

const STRUCTURED_OR_INCOME = /\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b/i;
const BROAD_BENCHMARK = /\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b/i;

export function isEligibleEtf(filing: NportFiling): boolean {
  if (STRUCTURED_OR_INCOME.test(filing.seriesName) || BROAD_BENCHMARK.test(filing.seriesName)) return false;
  const holdings = filing.holdings.filter((holding) => holding.weight > 0).sort((a, b) => b.weight - a.weight);
  if (holdings.length < 10 || holdings.length > 120) return false;
  const total = holdings.reduce((sum, holding) => sum + holding.weight, 0);
  const topTen = holdings.slice(0, 10).reduce((sum, holding) => sum + holding.weight, 0);
  return total >= 50 && topTen >= 25;
}

export function latestPublicFilings(filings: NportFiling[], asOf: string): NportFiling[] {
  const latest = new Map<string, NportFiling>();
  for (const filing of filings) {
    if (filing.filingDate > asOf) continue;
    const current = latest.get(filing.seriesId);
    if (!current || filing.filingDate > current.filingDate || (filing.filingDate === current.filingDate && filing.accession > current.accession)) latest.set(filing.seriesId, filing);
  }
  return [...latest.values()].filter(isEligibleEtf);
}
