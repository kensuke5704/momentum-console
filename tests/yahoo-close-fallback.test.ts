import assert from "node:assert/strict";
import test from "node:test";
import { validatedRegularCloseFallback, type IntradayPricePoint, type YahooHistorySnapshot } from "../src/lib/yahoo";

const session = (): IntradayPricePoint[] => Array.from({ length: 14 }, (_, index) => {
  const timestamp = new Date(Date.parse("2026-08-28T13:30:00.000Z") + index * 30 * 60_000).toISOString();
  const close = index === 13 ? 110 : 100 + index / 2;
  return { timestamp, open: index === 0 ? 100 : close - 0.1, close, high: close + 0.5, low: close - 0.5 };
});

const snapshot = (): YahooHistorySnapshot => ({
  points: [{ date: "2026-08-27", open: 99, close: 100 }],
  pendingLatest: { date: "2026-08-28", open: 100, high: 111, low: 99 },
  regularMarketPrice: 110,
  regularMarketTime: "2026-08-28T20:00:01.000Z",
});

test("builds a provisional daily row when the daily shell, full regular session, closing marker, and market price agree", () => {
  const point = validatedRegularCloseFallback(snapshot(), session(), new Date("2026-08-28T20:16:01.000Z"));
  assert.deepEqual(point, {
    date: "2026-08-28",
    open: 100,
    close: 110,
    high: 111,
    low: 99,
    provisional: true,
    source: "yahoo-validated-regular-close",
  });
});

test("does not use a regular-market price before the post-close validation buffer", () => {
  assert.equal(validatedRegularCloseFallback(snapshot(), session(), new Date("2026-08-28T20:15:00.000Z")), null);
});

test("fails closed when Yahoo market price and the closing marker disagree", () => {
  const bars = session();
  bars.at(-1)!.close = 109;
  assert.equal(validatedRegularCloseFallback(snapshot(), bars, new Date("2026-08-28T20:16:01.000Z")), null);
});

test("fails closed when the regular session is incomplete", () => {
  assert.equal(validatedRegularCloseFallback(snapshot(), session().slice(-7), new Date("2026-08-28T20:16:01.000Z")), null);
});

test("fails closed when the daily and intraday opening prices disagree", () => {
  const bars = session();
  bars[0].open = 90;
  assert.equal(validatedRegularCloseFallback(snapshot(), bars, new Date("2026-08-28T20:16:01.000Z")), null);
});

test("accepts a complete NYSE early-close session ending at 13:00 ET", () => {
  const bars = Array.from({ length: 8 }, (_, index) => {
    const timestamp = new Date(Date.parse("2026-11-27T14:30:00.000Z") + index * 30 * 60_000).toISOString();
    const close = index === 7 ? 105 : 100 + index / 2;
    return { timestamp, open: index === 0 ? 100 : close - 0.1, close, high: close + 0.5, low: close - 0.5 };
  });
  const earlyClose: YahooHistorySnapshot = {
    points: [],
    pendingLatest: { date: "2026-11-27", open: 100 },
    regularMarketPrice: 105,
    regularMarketTime: "2026-11-27T18:00:00.000Z",
  };
  assert.equal(validatedRegularCloseFallback(earlyClose, bars, new Date("2026-11-27T18:16:00.000Z"))?.close, 105);
});
