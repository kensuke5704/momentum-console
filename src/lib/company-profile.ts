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

const yahooHeaders = {
  "User-Agent": "Mozilla/5.0 MomentumConsole/2.0",
  Accept: "application/json",
};

const nasdaqHeaders = {
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
  Accept: "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.9",
  Referer: "https://www.nasdaq.com/",
};

async function fetchJson<T>(url: string, headers: Record<string, string> = yahooHeaders): Promise<T | null> {
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

const industryDetailJa: Record<string, string> = {
  "Semiconductors": "半導体や関連する設計技術・コンピューティング基盤を扱う分野です。主な需要先にはデータセンター、AI、PC、通信、産業機器、自動車などが含まれます。製品性能に加え、ソフトウェアとの統合、供給能力、開発スピードが競争力を左右します。",
  "Software - Infrastructure": "企業や政府機関のIT基盤、データ処理、セキュリティ、クラウド運用などを支えるソフトウェア分野です。大口顧客との長期契約やサブスクリプション収入が中心となりやすく、顧客基盤の拡大、契約単価、継続利用率が成長を左右します。",
  "Software - Application": "企業や個人が日常業務や特定用途で利用するアプリケーションソフトウェアを提供する分野です。サブスクリプション型の収益モデルが多く、利用者数、契約単価、継続率、新機能の投入、周辺サービスとの連携が重要です。",
  "Computer Hardware": "コンピューター、計算機器、周辺装置、専用ハードウェアなどを扱う分野です。製品性能だけでなく、開発サイクル、製造・調達体制、ソフトウェアやクラウドサービスとの組み合わせが競争上の重要要素です。",
  "Information Technology Services": "企業向けのIT導入、運用、コンサルティング、データ処理などを提供する分野です。長期契約や継続的なサービス収入が中心となりやすく、大口顧客との関係、人材、技術力、プロジェクト遂行能力が競争力につながります。",
  "Internet Content & Information": "インターネット上のコンテンツ、情報流通、広告、データサービスなどを扱う分野です。利用者規模、エンゲージメント、広告・課金モデル、保有データの価値、ネットワーク効果が収益力に直結しやすい特徴があります。",
  "Communication Equipment": "通信ネットワークや接続機器、関連ハードウェアを提供する分野です。通信事業者や企業の設備投資サイクルの影響を受けやすく、性能、信頼性、規格対応、導入済み顧客基盤が競争力を左右します。",
  "Consumer Electronics": "一般消費者向けの電子機器や関連製品を扱う分野です。ブランド力、製品サイクル、価格競争、流通網、エコシステムとの連携が業績に影響しやすい分野です。",
  "Aerospace & Defense": "ロケット、人工衛星、防衛装備、航空宇宙システムや関連サービスを扱う分野です。政府・防衛機関や商業顧客との大型契約が多く、技術実証、打ち上げ・製造能力、受注残、規制対応が成長を左右します。",
  "Biotechnology": "生命科学を活用して医薬品や治療技術を研究・開発する分野です。研究開発成果、臨床試験、規制承認、提携契約などが企業価値に大きく影響し、製品化前は収益や株価の変動が大きくなりやすい特徴があります。",
  "Medical Devices": "診断・治療に用いる医療機器や関連サービスを提供する分野です。医療機関への採用、規制承認、保険償還、製品の安全性と臨床上の有効性、継続消耗品の販売などが成長の主要因です。",
  "Auto Manufacturers": "自動車や関連モビリティ製品を開発・製造する分野です。販売台数、車種構成、価格、製造効率に加え、EV、自動運転、車載ソフトウェアへの対応が競争力を左右します。",
  "Electrical Equipment & Parts": "電力制御、電子部品、電気設備などを供給する分野です。産業設備、データセンター、エネルギーインフラなどの設備投資需要の影響を受けやすく、製品性能、供給能力、顧客との長期関係が重要です。",
  "Specialty Industrial Machinery": "特定用途向けの産業機械や自動化設備を提供する分野です。製造業の設備投資や自動化需要との連動性が高く、技術力、受注残、導入後の保守・サービス収入が収益性に影響します。",
  "Capital Markets": "証券取引、投資銀行、資産運用、マーケットメイクなど資本市場に関連する金融サービスを提供する分野です。市場環境、取引量、運用資産残高、金利や信用環境の変化が収益に影響します。",
};

function normalizeIndustry(value: string | null): string | null {
  return value?.replace(/[—–]/g, " - ").replace(/\s+/g, " ").trim() ?? null;
}

function japaneseMetadataSummary(companyName: string, industry: string | null, sector: string | null): string {
  const normalizedIndustry = normalizeIndustry(industry);
  const industryLabel = normalizedIndustry ? industryJa[normalizedIndustry] ?? normalizedIndustry : null;
  const sectorLabel = sector ? sectorJa[sector] ?? sector : null;
  const intro = industryLabel && sectorLabel
    ? `${companyName}は、${sectorLabel}セクターに属し、主に${industryLabel}分野で事業を展開する企業です。`
    : industryLabel
      ? `${companyName}は、主に${industryLabel}分野で事業を展開する企業です。`
      : sectorLabel
        ? `${companyName}は、${sectorLabel}セクターに属する企業です。`
        : `${companyName}は米国株式市場で取引されている企業です。`;
  const detail = normalizedIndustry ? industryDetailJa[normalizedIndustry] : null;
  return detail ? `${intro}${detail}` : `${intro}主な製品・サービス、顧客層、収益源などの詳細情報は公開企業情報をもとに順次補完します。`;
}

async function translateBusinessSummaryToJapanese(summary: string): Promise<string | null> {
  const source = summary.trim().slice(0, 5000);
  if (!source) return null;
  try {
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ja&dt=t&q=${encodeURIComponent(source)}`;
    const response = await fetch(url, { headers: yahooHeaders, signal: AbortSignal.timeout(15000) });
    if (!response.ok) return null;
    const body = await response.json() as unknown;
    if (!Array.isArray(body) || !Array.isArray(body[0])) return null;
    const translated = body[0]
      .map((item) => Array.isArray(item) && typeof item[0] === "string" ? item[0] : "")
      .join("")
      .replace(/\s+/g, " ")
      .trim();
    return translated.length >= 40 ? translated : null;
  } catch {
    return null;
  }
}

function findDescription(value: unknown, depth = 0): string | null {
  if (depth > 6 || value == null) return null;
  if (typeof value === "object" && !Array.isArray(value)) {
    const record = value as Record<string, unknown>;
    for (const key of ["companyDescription", "businessDescription", "longBusinessSummary", "description"]) {
      const candidate = record[key];
      if (typeof candidate === "string" && candidate.trim().length >= 80) return candidate.trim();
      if (candidate && typeof candidate === "object") {
        const nested = candidate as Record<string, unknown>;
        for (const subkey of ["value", "label", "text"]) {
          if (typeof nested[subkey] === "string" && String(nested[subkey]).trim().length >= 80) return String(nested[subkey]).trim();
        }
      }
    }
    for (const child of Object.values(record)) {
      const found = findDescription(child, depth + 1);
      if (found) return found;
    }
  } else if (Array.isArray(value)) {
    for (const child of value) {
      const found = findDescription(child, depth + 1);
      if (found) return found;
    }
  }
  return null;
}

async function fetchNasdaqBusinessSummary(symbol: string): Promise<string | null> {
  const body = await fetchJson<unknown>(`https://api.nasdaq.com/api/company/${encodeURIComponent(symbol)}/company-profile`, nasdaqHeaders);
  return findDescription(body);
}

async function buildJapaneseSummary(
  symbol: string,
  companyName: string,
  industry: string | null,
  sector: string | null,
  englishBusinessSummary?: string | null,
): Promise<string> {
  const source = englishBusinessSummary?.trim() || await fetchNasdaqBusinessSummary(symbol);
  if (source) {
    const translated = await translateBusinessSummaryToJapanese(source);
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
      yahooHeaders,
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
        summary: await buildJapaneseSummary(symbol, name, industry, sector, row.assetProfile?.longBusinessSummary),
        website: row.assetProfile?.website ?? null,
        updatedAt: now,
      };
    }
  }

  const search = await fetchJson<YahooSearchResponse>(
    `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(symbol)}&quotesCount=8&newsCount=0&listsCount=0`,
    yahooHeaders,
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
    summary: await buildJapaneseSummary(symbol, name, industry, sector),
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
          summary: prior?.summary && /[ぁ-んァ-ヶ一-龠]/.test(prior.summary) && prior.summary.length >= 80
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
