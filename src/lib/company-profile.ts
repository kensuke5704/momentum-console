// Company summaries shown in the UI are always emitted in Japanese.
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

function normalizeIndustry(value: string | null): string | null {
  return value?.replace(/[—–]/g, " - ").replace(/\s+/g, " ").trim() ?? null;
}

function japaneseMetadataSummary(companyName: string, industry: string | null, sector: string | null): string {
  const normalizedIndustry = normalizeIndustry(industry);
  const industryLabel = normalizedIndustry ? industryJa[normalizedIndustry] ?? null : null;
  const sectorLabel = sector ? sectorJa[sector] ?? null : null;
  if (industryLabel && sectorLabel) return `${companyName}は、${sectorLabel}セクターに属し、主に${industryLabel}分野で事業を展開する企業です。`;
  if (industryLabel) return `${companyName}は、主に${industryLabel}分野で事業を展開する企業です。`;
  if (sectorLabel) return `${companyName}は、${sectorLabel}セクターに属する企業です。`;
  return `${companyName}は米国株式市場で取引されている企業です。`;
}

async function translateBusinessSummaryToJapanese(summary: string): Promise<string | null> {
  const source = summary.trim().slice(0, 3500);
  if (!source) return null;
  try {
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ja&dt=t&q=${encodeURIComponent(source)}`;
    const response = await fetch(url, { headers, signal: AbortSignal.timeout(15000) });
    if (!response.ok) return null;
    const body = await response.json() as unknown;
    if (!Array.isArray(body) || !Array.isArray(body[0])) return null;
    const translated = body[0]
      .map((item) => Array.isArray(item) && typeof item[0] === "string" ? item[0] : "")
      .join("")
      .trim();
    return translated.length >= 20 ? translated : null;
  } catch {
    return null;
  }
}

async function buildJapaneseSummary(
  companyName: string,
  industry: string | null,
  sector: string | null,
  englishBusinessSummary?: string | null,
): Promise<string> {
  if (englishBusinessSummary) {
    const translated = await translateBusinessSummaryToJapanese(englishBusinessSummary);
    if (translated) return translated;
  }
  return japaneseMetadataSummary(companyName, industry, sector);
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
        summary: await buildJapaneseSummary(name, industry, sector, row.assetProfile?.longBusinessSummary),
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
    summary: japaneseMetadataSummary(name, industry, sector),
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
        output[symbol] = {
          symbol,
          companyName: prior?.companyName ?? symbol,
          industry: prior?.industry ?? null,
          sector: prior?.sector ?? null,
          summary: prior?.summary && /[ぁ-んァ-ヶ一-龠]/.test(prior.summary)
            ? prior.summary
            : japaneseMetadataSummary(prior?.companyName ?? symbol, prior?.industry ?? null, prior?.sector ?? null),
          website: prior?.website ?? null,
          updatedAt: new Date().toISOString(),
        };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, Math.max(1, symbols.length)) }, () => worker()));
  return output;
}
