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
    error?: {
      description?: string;
    } | null;
  };
};

type YahooBatchResponse = {
  histories?: Record<string, PricePoint[]>;
  errors?: string[];
  error?: string;
};

export type YahooBatchResult = {
  histories: Record<string, PricePoint[]>;
  errors: string[];
};

const YAHOO_PROXY_URL =
  "https://script.google.com/macros/s/AKfycbxdoPfdFumjndzTE67Meu-rNZqBDhU0ja63ZsLjOiNHaQvwgfsKEHzR92yTiAkueKhv/exec";

function parseYahooHistory(
  symbol: string,
  body: YahooChartResponse,
): PricePoint[] {
  const result = body.chart?.result?.[0];
  if (!result?.timestamp?.length) {
    throw new Error(
      body.chart?.error?.description ??
        `${symbol}の価格履歴が見つかりませんでした。`,
    );
  }

  const closes =
    result.indicators?.adjclose?.[0]?.adjclose ??
    result.indicators?.quote?.[0]?.close ??
    [];

  const points = result.timestamp
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

  if (points.length < 12) {
    throw new Error(`${symbol}は比較に必要な価格履歴が不足しています。`);
  }

  return points;
}

function loadJsonp<T>(
  params: URLSearchParams,
  timeoutMs: number,
  errorMessage: string,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const callbackName =
      `__momentumYahoo_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const callbackHost = window as unknown as Record<string, unknown>;
    const script = document.createElement("script");
    let settled = false;

    function cleanup() {
      window.clearTimeout(timeout);
      script.remove();
      delete callbackHost[callbackName];
    }

    function fail(message: string) {
      if (settled) return;
      settled = true;
      cleanup();
      reject(new Error(message));
    }

    callbackHost[callbackName] = (body: T) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(body);
    };

    const timeout = window.setTimeout(
      () => fail(`${errorMessage} 時間をおいて再度お試しください。`),
      timeoutMs,
    );

    params.set("callback", callbackName);
    script.async = true;
    script.onerror = () => fail(errorMessage);
    script.src = `${YAHOO_PROXY_URL}?${params.toString()}`;
    document.head.appendChild(script);
  });
}

export async function fetchYahooHistoryInBrowser(
  symbol: string,
): Promise<PricePoint[]> {
  const normalizedSymbol = symbol.trim().toUpperCase();
  const body = await loadJsonp<YahooChartResponse>(
    new URLSearchParams({ symbol: normalizedSymbol }),
    30000,
    `${normalizedSymbol}をYahoo Financeから取得できませんでした。`,
  );
  return parseYahooHistory(normalizedSymbol, body);
}

export async function fetchYahooHistoriesInBrowser(
  symbols: string[],
): Promise<YahooBatchResult> {
  const normalizedSymbols = [
    ...new Set(symbols.map((symbol) => symbol.trim().toUpperCase())),
  ].filter(Boolean);
  if (!normalizedSymbols.length) return { histories: {}, errors: [] };

  const body = await loadJsonp<YahooBatchResponse>(
    new URLSearchParams({ symbols: normalizedSymbols.join(",") }),
    45000,
    "Yahoo Financeから最新価格を取得できませんでした。",
  );
  if (body.error) throw new Error(body.error);

  const histories = Object.fromEntries(
    Object.entries(body.histories ?? {}).filter(([, points]) =>
      Array.isArray(points) && points.length >= 12
    ),
  );
  const errors = body.errors ?? [];
  if (!Object.keys(histories).length) {
    throw new Error(
      errors[0] ?? "Yahoo Financeから価格履歴を取得できませんでした。",
    );
  }

  return { histories, errors };
}
