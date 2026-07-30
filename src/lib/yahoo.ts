import type { PricePoint } from "./types";

type YahooChartResponse = {
  chart?: {
    result?: Array<{
      timestamp?: number[];
      indicators?: {
        adjclose?: Array<{ adjclose?: Array<number | null> }>;
        quote?: Array<{ close?: Array<number | null> }>;
      };
    }>;
    error?: unknown;
  };
};

const START_UNIX = Math.floor(
  new Date("2020-01-01T00:00:00Z").getTime() / 1000,
);

export async function fetchYahooHistory(symbol: string): Promise<PricePoint[]> {
  const endUnix = Math.floor(Date.now() / 1000) + 86400;
  const yahooSymbol = encodeURIComponent(symbol.replace(".", "-"));
  const url =
    `https://query1.finance.yahoo.com/v8/finance/chart/${yahooSymbol}` +
    `?period1=${START_UNIX}&period2=${endUnix}&interval=1d` +
    "&events=history&includeAdjustedClose=true";

  const response = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 MomentumConsole/1.0",
      Accept: "application/json",
    },
    next: { revalidate: 21600 },
    signal: AbortSignal.timeout(15000),
  });

  if (!response.ok) {
    throw new Error(`${symbol}: market data request failed (${response.status})`);
  }

  const body = (await response.json()) as YahooChartResponse;
  const result = body.chart?.result?.[0];

  if (!result?.timestamp?.length) {
    throw new Error(`${symbol}: no price history returned`);
  }

  const closes =
    result.indicators?.adjclose?.[0]?.adjclose ??
    result.indicators?.quote?.[0]?.close ??
    [];

  return result.timestamp
    .map((timestamp, index) => {
      const close = closes[index];
      if (typeof close !== "number" || !Number.isFinite(close) || close <= 0) {
        return null;
      }

      return {
        date: new Date(timestamp * 1000).toISOString().slice(0, 10),
        close,
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
      output[symbol] = await fetchYahooHistory(symbol);
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
