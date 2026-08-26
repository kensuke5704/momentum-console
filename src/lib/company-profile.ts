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

type WikipediaQueryResponse = {
  query?: { pages?: Record<string, { extract?: string }> };
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

async function fetchJapaneseWikipediaSummary(companyName: string, symbol: string): Promise<string | null> {
  for (const query of [companyName, `${companyName} 企業`, symbol]) {
    const body = await fetchJson<WikipediaQueryResponse>(
      `https://ja.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch=${encodeURIComponent(query)}&gsrlimit=1&prop=extracts&exintro=1&explaintext=1&redirects=1&format=json&origin=*`,
    );
    const page = Object.values(body?.query?.pages ?? {})[0];
    const extract = page?.extract?.trim();
    if (extract && extract.length >= 30) return extract;
  }
  return null;
}

const industryJa: Record<string, string> = {
  "Semiconductors": "半導体",
  "Software - Infrastructure": "インフラソフトウェア",
  "Software - Application": "アプリケーションソフトウェア",
  "Computer Hardware": "コンピューターハードウェア",
  "Information Technology Services": "ITサービス",
  "Internet Content & Information": "インターネットコンテンツ・情報サービス",
  "Communication Equipment": "通信機器",
  "Consumer Electronics": "民生用電子機器",
  "Aerospace & Defense": "航空宇宙・防衛",
  "Biotechnology": "バイオテクノロジー",
  "Medical Devices": "医療機器",
  "Auto Manufacturers": "自動車",
  "Electrical Equipment & Parts": "電気機器・部品",
  "Specialty Industrial Machinery": "産業機械",
  "Capital Markets": "資本市場・金融サービス",
};

const sectorJa: Record<string, string> = {
  "Technology": "情報技術",
  "Communication Services": "コミュニケーション・サービス",
  "Industrials": "資本財・産業",
  "Healthcare": "ヘルスケア",
  "Consumer Cyclical": "一般消費財",
  "Consumer Defensive": "生活必需品",
  "Financial Services": "金融",
  "Energy": "エネルギー",
  "Basic Materials": "素材",
  "Real Estate": "不動産",
  "Utilities": "公益",
};

function japaneseMetadataSummary(companyName: string, industry: string | null, sector: string | null): string {
  const industryLabel = industry ? (industryJa[industry] ?? industry) : null;
  const sectorLabel = sector ? (sectorJa[sector] ?? sector) : null;
  if (industryLabel && sectorLabel) return `${companyName}は、${sectorLabel}セクターに属し、主に${industryLabel}分野で事業を展開する企業です。`;
  if (industryLabel) return `${companyName}は、主に${industryLabel}分野で事業を展開する企業です。`;
  if (sectorLabel) return `${companyName}は、${sectorLabel}セクターに属する企業です。`;
  return `${companyName}は米国株式市場で取引されている企業です。詳細な事業概要は公開情報から順次補完します。`;
}

async function buildJapaneseSummary(companyName: string, symbol: string, industry: string | null, sector: string | null): Promise<string> {
  return await fetchJapaneseWikipediaSummary(companyName, symbol)
    ?? japaneseMetadataSummary(companyName, industry, sector);
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
      const industry = row.assetProfile?.industry ?? null;
      const sector = row.assetProfile?.sector ?? null;
      return {
        symbol,
        companyName: name,
        industry,
        sector,
        summary: await buildJapaneseSummary(name, symbol, industry, sector),
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
  const industry = quote.industry ?? null;
  const sector = quote.sector ?? null;
  return {
    symbol,
    companyName: name,
    industry,
    sector,
    summary: await buildJapaneseSummary(name, symbol, industry, sector),
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
      else {
        const prior = output[symbol];
        output[symbol] = prior?.summary ? prior : {
          symbol,
          companyName: prior?.companyName ?? symbol,
          industry: prior?.industry ?? null,
          sector: prior?.sector ?? null,
          summary: japaneseMetadataSummary(prior?.companyName ?? symbol, prior?.industry ?? null, prior?.sector ?? null),
          website: prior?.website ?? null,
          updatedAt: new Date().toISOString(),
        };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, Math.max(1, symbols.length)) }, () => worker()));
  return output;
}
