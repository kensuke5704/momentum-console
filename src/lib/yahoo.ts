import type { PricePoint } from "./types";

type YahooChartResponse = {
  chart?: {
    result?: Array<{
      timestamp?: number[];
      indicators?: {
        adjclose?: Array<{ adjclose?: Array<number | null> }>;
        quote?: Array<{
          close?: Array<number | null>;
          open?: Array<number | null>;
          high?: Array<number | null>;
          low?: Array<number | null>;
        }>;
      };
    }>;
    error?: unknown;
  };
};

const START_UNIX = Math.floor(
  new Date("2018-01-01T00:00:00Z").getTime() / 1000,
);

export async function fetchYahooHistory(symbol: string): Promise<PricePoint[]> {
  const endUnix = Math.floor(Date.now() / 1000) + 86400;
  const yahooSymbol = encodeURIComponent(symbol.replace(".", "-"));
  let body: YahooChartResponse | null = null;
  let lastStatus = 0;
  for (let attempt = 0; attempt < 4; attempt++) {
    const host = attempt % 2 === 0 ? "query1.finance.yahoo.com" : "query2.finance.yahoo.com";
    const url = `https://${host}/v8/finance/chart/${yahooSymbol}?period1=${START_UNIX}&period2=${endUnix}&interval=1d&events=history&includeAdjustedClose=true`;
    const response = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0 MomentumConsole/2.0", Accept: "application/json" }, next: { revalidate: 21600 }, signal: AbortSignal.timeout(20000) });
    lastStatus = response.status;
    if (response.ok) { body = (await response.json()) as YahooChartResponse; break; }
    if (attempt < 3) await new Promise((resolve) => setTimeout(resolve, 350 * (attempt + 1)));
  }
  if (!body) throw new Error(`${symbol}: market data request failed (${lastStatus})`);
  const result = body.chart?.result?.[0];

  if (!result?.timestamp?.length) {
    throw new Error(`${symbol}: no price history returned`);
  }

  const quote = result.indicators?.quote?.[0];
  const closes =
    result.indicators?.adjclose?.[0]?.adjclose ??
    quote?.close ??
    [];

  return result.timestamp
    .map((timestamp, index) => {
      const close = closes[index];
      if (typeof close !== "number" || !Number.isFinite(close) || close <= 0) {
        return null;
      }

      const rawClose = quote?.close?.[index];
      const rawOpen = quote?.open?.[index];
      if (typeof rawClose !== "number" || rawClose <= 0 || typeof rawOpen !== "number" || rawOpen <= 0) return null;
      // Yahoo's adjusted close incorporates splits/dividends. Apply the same
      // factor to OHLC so a split cannot create a false stop or impossible
      // adjusted-close/unadjusted-open execution return.
      const factor = close / rawClose;
      const open = rawOpen * factor;
      const rawHigh = quote?.high?.[index];
      const rawLow = quote?.low?.[index];
      const high = typeof rawHigh === "number" ? rawHigh * factor : undefined;
      const low = typeof rawLow === "number" ? rawLow * factor : undefined;
      return {
        date: new Date(timestamp * 1000).toISOString().slice(0, 10),
        close,
        open,
        ...(typeof high === "number" && Number.isFinite(high) ? { high } : {}),
        ...(typeof low === "number" && Number.isFinite(low) ? { low } : {}),
      };
    })
    .filter((point): point is PricePoint => point !== null);
}

export async function fetchHistories(
  symbols: string[],
  concurrency = 6,
): Promise<Record<string, PricePoint[]>> {
  const output: Record<string, PricePoint[]> = {};
  let cursor = 0;

  async function worker() {
    while (cursor < symbols.length) {
      const index = cursor;
      cursor += 1;
      const symbol = symbols[index];
      try {
        output[symbol] = await fetchYahooHistory(symbol);
      } catch (error) {
        console.warn(error instanceof Error ? error.message : `${symbol}: price fetch failed`);
        output[symbol] = [];
      }
    }
  }

  await Promise.all(
    Array.from(
      { length: Math.min(concurrency, symbols.length) },
      () => worker(),
    ),
  );

  return output;
}

export type IntradayPricePoint = {
  timestamp: string;
  close: number;
  open: number;
  high: number;
  low: number;
};

export async function fetchYahooIntraday(
  symbol: string,
): Promise<IntradayPricePoint[]> {
  const yahooSymbol = encodeURIComponent(symbol.replace(".", "-"));
  const url =
    `https://query1.finance.yahoo.com/v8/finance/chart/${yahooSymbol}` +
    "?range=5d&interval=30m&includePrePost=false";
  const response = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 MomentumConsole/1.0",
      Accept: "application/json",
    },
    signal: AbortSignal.timeout(15000),
  });

  if (!response.ok) {
    throw new Error(`${symbol}: intraday data request failed (${response.status})`);
  }

  const body = (await response.json()) as YahooChartResponse;
  const result = body.chart?.result?.[0];
  const quote = result?.indicators?.quote?.[0];
  const closes = quote?.close ?? [];

  return (result?.timestamp ?? [])
    .map((timestamp, index) => {
      const close = closes[index];
      const open = quote?.open?.[index], high = quote?.high?.[index], low = quote?.low?.[index];
      if (typeof close !== "number" || !Number.isFinite(close) || close <= 0 || typeof open !== "number" || typeof high !== "number" || typeof low !== "number") {
        return null;
      }
      return { timestamp: new Date(timestamp * 1000).toISOString(), close, open, high, low };
    })
    .filter((point): point is IntradayPricePoint => point !== null);
}

export async function fetchIntradayHistories(
  symbols: string[],
  concurrency = 6,
): Promise<Record<string, IntradayPricePoint[]>> {
  const output: Record<string, IntradayPricePoint[]> = {};
  let cursor = 0;
  async function worker() {
    while (cursor < symbols.length) {
      const symbol = symbols[cursor++];
      try {
        output[symbol] = await fetchYahooIntraday(symbol);
      } catch (error) {
        console.warn(error instanceof Error ? error.message : `${symbol}: intraday fetch failed`);
        output[symbol] = [];
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, symbols.length) }, () => worker()));
  return output;
}
