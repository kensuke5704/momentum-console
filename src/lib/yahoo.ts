import type { PricePoint } from "./types";

type YahooChartResponse = {
  chart?: {
    result?: Array<{
      meta?: {
        regularMarketPrice?: number;
        regularMarketTime?: number;
        exchangeTimezoneName?: string;
      };
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

export type YahooPendingDailyPoint = {
  date: string;
  open: number;
  high?: number;
  low?: number;
};

export type YahooHistorySnapshot = {
  points: PricePoint[];
  pendingLatest?: YahooPendingDailyPoint;
  regularMarketPrice?: number;
  regularMarketTime?: string;
};

const positive = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value > 0;

const localParts = (timestamp: string) => Object.fromEntries(
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(timestamp)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]),
);

const localDate = (timestamp: string) => {
  const parts = localParts(timestamp);
  return `${parts.year}-${parts.month}-${parts.day}`;
};

const closeEnough = (left: number, right: number, absoluteTolerance: number) =>
  Math.abs(left - right) <= Math.max(absoluteTolerance, Math.max(left, right) * 0.00001);

/**
 * Builds a provisional daily row only when independent Yahoo fields agree on
 * the completed regular-session close. It deliberately fails closed when any
 * timestamp, price, opening-auction, or bar-coverage check is inconsistent.
 */
export function validatedRegularCloseFallback(
  snapshot: YahooHistorySnapshot,
  intraday: IntradayPricePoint[],
  now = new Date(),
): PricePoint | null {
  const pending = snapshot.pendingLatest;
  const marketTime = snapshot.regularMarketTime;
  const marketPrice = snapshot.regularMarketPrice;
  if (!pending || !marketTime || !positive(marketPrice)) return null;
  if (localDate(marketTime) !== pending.date) return null;

  const time = localParts(marketTime);
  const isNormalClose = time.hour === "16" && time.minute === "00";
  const isEarlyClose = time.hour === "13" && time.minute === "00";
  if (!isNormalClose && !isEarlyClose) return null;
  if (now.getTime() < Date.parse(marketTime) + 15 * 60_000) return null;

  const session = intraday
    .filter((point) => localDate(point.timestamp) === pending.date && point.timestamp <= marketTime)
    .sort((left, right) => left.timestamp.localeCompare(right.timestamp));
  // A full early-close session has at least seven 30-minute bars plus Yahoo's
  // closing marker; a normal session has fourteen observations.
  if (session.length < 8) return null;
  const first = session[0], last = session.at(-1)!;
  const firstTime = localParts(first.timestamp);
  if (firstTime.hour !== "09" || firstTime.minute !== "30") return null;
  // Yahoo regularMarketTime can trail its synthetic 16:00 closing marker by
  // one second. Permit only a tiny metadata skew, never a missing final bar.
  if (Math.abs(Date.parse(last.timestamp) - Date.parse(marketTime)) > 5_000) return null;
  if (!closeEnough(first.open, pending.open, 0.02)) return null;
  if (!closeEnough(last.close, marketPrice, 0.02)) return null;

  const highs = session.map((point) => point.high);
  const lows = session.map((point) => point.low);
  if (positive(pending.high)) highs.push(pending.high);
  if (positive(pending.low)) lows.push(pending.low);
  return {
    date: pending.date,
    open: pending.open,
    close: marketPrice,
    high: Math.max(...highs),
    low: Math.min(...lows),
    provisional: true,
    source: "yahoo-validated-regular-close",
  };
}

export async function fetchYahooHistorySnapshot(symbol: string): Promise<YahooHistorySnapshot> {
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
  const adjustedCloses = result.indicators?.adjclose?.[0]?.adjclose;
  let pendingLatest: YahooPendingDailyPoint | undefined;
  const points = result.timestamp
    .map<PricePoint | null>((timestamp, index) => {
      const close = adjustedCloses ? adjustedCloses[index] : quote?.close?.[index];
      const rawClose = quote?.close?.[index];
      const rawOpen = quote?.open?.[index];
      if (!positive(close) || !positive(rawClose) || !positive(rawOpen)) {
        if (index === result.timestamp!.length - 1 && positive(rawOpen)) {
          const rawHigh = quote?.high?.[index], rawLow = quote?.low?.[index];
          pendingLatest = {
            date: new Date(timestamp * 1000).toISOString().slice(0, 10),
            open: rawOpen,
            ...(positive(rawHigh) ? { high: rawHigh } : {}),
            ...(positive(rawLow) ? { low: rawLow } : {}),
          };
        }
        return null;
      }
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
  const regularMarketTime = result.meta?.regularMarketTime;
  return {
    points,
    ...(pendingLatest ? { pendingLatest } : {}),
    ...(positive(result.meta?.regularMarketPrice) ? { regularMarketPrice: result.meta.regularMarketPrice } : {}),
    ...(typeof regularMarketTime === "number" ? { regularMarketTime: new Date(regularMarketTime * 1000).toISOString() } : {}),
  };
}

export async function fetchYahooHistory(symbol: string): Promise<PricePoint[]> {
  return (await fetchYahooHistorySnapshot(symbol)).points;
}

export async function fetchHistorySnapshots(
  symbols: string[],
  concurrency = 6,
): Promise<Record<string, YahooHistorySnapshot>> {
  const output: Record<string, YahooHistorySnapshot> = {};
  let cursor = 0;
  async function worker() {
    while (cursor < symbols.length) {
      const symbol = symbols[cursor++];
      try {
        output[symbol] = await fetchYahooHistorySnapshot(symbol);
      } catch (error) {
        console.warn(error instanceof Error ? error.message : `${symbol}: price fetch failed`);
        output[symbol] = { points: [] };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, symbols.length) }, () => worker()));
  return output;
}

export async function fetchHistories(
  symbols: string[],
  concurrency = 6,
): Promise<Record<string, PricePoint[]>> {
  const snapshots = await fetchHistorySnapshots(symbols, concurrency);
  return Object.fromEntries(symbols.map((symbol) => [symbol, snapshots[symbol]?.points ?? []]));
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
