export type CompanyProfile = {
  symbol: string;
  companyName: string;
  industry: string | null;
  sector: string | null;
  summary: string | null;
  website: string | null;
  updatedAt: string;
};

type YahooQuoteSummaryResponse = {
  quoteSummary?: {
    result?: Array<{
      price?: { longName?: string; shortName?: string };
      assetProfile?: {
        industry?: string;
        sector?: string;
        longBusinessSummary?: string;
        website?: string;
      };
    }>;
  };
};

type YahooSearchResponse = {
  quotes?: Array<{
    symbol?: string;
    longname?: string;
    shortname?: string;
    industry?: string;
    sector?: string;
  }>;
};

const headers = {
  "User-Agent": "Mozilla/5.0 MomentumConsole/2.0",
  Accept: "application/json",
};

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url, { headers, signal: AbortSignal.timeout(15000) });
    if (!response.ok) return null;
    return await response.json() as T;
  } catch {
    return null;
  }
}

export async function fetchCompanyProfile(symbol: string): Promise<CompanyProfile | null> {
  const yahooSymbol = encodeURIComponent(symbol.replace(".", "-"));
  const now = new Date().toISOString();
  for (const host of ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]) {
    const body = await fetchJson<YahooQuoteSummaryResponse>(
      `https://${host}/v10/finance/quoteSummary/${yahooSymbol}?modules=price,assetProfile`,
    );
    const row = body?.quoteSummary?.result?.[0];
    if (!row) continue;
    const name = row.price?.longName ?? row.price?.shortName;
    if (name) {
      return {
        symbol,
        companyName: name,
        industry: row.assetProfile?.industry ?? null,
        sector: row.assetProfile?.sector ?? null,
        summary: row.assetProfile?.longBusinessSummary ?? null,
        website: row.assetProfile?.website ?? null,
        updatedAt: now,
      };
    }
  }

  const search = await fetchJson<YahooSearchResponse>(
    `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(symbol)}&quotesCount=8&newsCount=0&listsCount=0`,
  );
  const quote = search?.quotes?.find((row) => row.symbol?.toUpperCase() === symbol.replace(".", "-").toUpperCase())
    ?? search?.quotes?.find((row) => row.symbol?.toUpperCase() === symbol.toUpperCase());
  if (!quote) return null;
  const name = quote.longname ?? quote.shortname;
  if (!name) return null;
  return {
    symbol,
    companyName: name,
    industry: quote.industry ?? null,
    sector: quote.sector ?? null,
    summary: null,
    website: null,
    updatedAt: now,
  };
}

export async function fetchCompanyProfiles(
  symbols: string[],
  existing: Record<string, CompanyProfile> = {},
  concurrency = 4,
): Promise<Record<string, CompanyProfile>> {
  const output: Record<string, CompanyProfile> = { ...existing };
  let cursor = 0;
  async function worker() {
    while (cursor < symbols.length) {
      const symbol = symbols[cursor++];
      const profile = await fetchCompanyProfile(symbol);
      if (profile) output[symbol] = profile;
      else if (!output[symbol]) {
        output[symbol] = {
          symbol,
          companyName: symbol,
          industry: null,
          sector: null,
          summary: null,
          website: null,
          updatedAt: new Date().toISOString(),
        };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, Math.max(1, symbols.length)) }, () => worker()));
  return output;
}
