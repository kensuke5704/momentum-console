import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildDashboardPayload } from "../src/lib/dashboard";
import { runStrategySimulation } from "../src/lib/backtest";
import { fetchCompanyProfiles, type CompanyProfile } from "../src/lib/company-profile";
import { previousUsTradingSession } from "../src/lib/trading-calendar";
import type { BacktestResult, ForwardOosResult, NportOperations, PricePoint, UniverseMonth } from "../src/lib/types";
import { fetchHistorySnapshots, fetchIntradayHistories, type IntradayPricePoint, validatedRegularCloseFallback } from "../src/lib/yahoo";

type UniverseFile = { history: UniverseMonth[] };
type MarketDataFile = { histories?: Record<string, PricePoint[]>; intraday?: Record<string, IntradayPricePoint[]> };
type CompanyProfileFile = { generatedAt?: string; profiles?: Record<string, CompanyProfile> };

async function existingHistories(path: string): Promise<Record<string, PricePoint[]>> {
  try { return (JSON.parse(await readFile(path, "utf8")) as MarketDataFile).histories ?? {}; } catch { return {}; }
}
async function existingMarketData(path: string): Promise<MarketDataFile> {
  try { return JSON.parse(await readFile(path, "utf8")) as MarketDataFile; } catch { return {}; }
}
async function existingCompanyProfiles(path: string): Promise<Record<string, CompanyProfile>> {
  try { return (JSON.parse(await readFile(path, "utf8")) as CompanyProfileFile).profiles ?? {}; } catch { return {}; }
}
async function optionalJson<T>(path: string): Promise<T | undefined> {
  try { return JSON.parse(await readFile(path, "utf8")) as T; } catch { return undefined; }
}
function mergeIntraday(existing: Record<string, IntradayPricePoint[]>, fetched: Record<string, IntradayPricePoint[]>, symbols: string[]) {
  return Object.fromEntries(symbols.map((symbol) => {
    const fresh = fetched[symbol] ?? [];
    if (!fresh.length) return [symbol, existing[symbol] ?? []];
    const byTimestamp = new Map<string, IntradayPricePoint>();
    for (const point of existing[symbol] ?? []) byTimestamp.set(point.timestamp, point);
    for (const point of fresh) byTimestamp.set(point.timestamp, point);
    return [symbol, [...byTimestamp.values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-80)];
  }));
}
function merge(existing: Record<string, PricePoint[]>, fetched: Record<string, PricePoint[]>, symbols: string[]) {
  return Object.fromEntries(symbols.map((symbol) => {
    const byDate = new Map<string, PricePoint>();
    for (const point of existing[symbol] ?? []) byDate.set(point.date, point);
    for (const point of fetched[symbol] ?? []) byDate.set(point.date, point);
    return [symbol, [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date))];
  }));
}
async function main() {
  const universeFile = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const universeHistory = universeFile.history;
  if (!universeHistory.length) throw new Error("Dynamic Universe history is empty; run npm run sync:universe first");
  const symbols = [...new Set(["QQQ", "TQQQ", ...universeHistory.flatMap((month) => month.symbols.map((member) => member.symbol))])];
  const currentSymbols = [...new Set(universeHistory.at(-1)?.symbols.map((member) => member.symbol) ?? [])];
  const intradaySymbols = [...new Set(["QQQ", "TQQQ", ...currentSymbols])];
  console.log(`Fetching adjusted OHLC for ${symbols.length} dynamic-universe symbols`);
  const outputPath = resolve("public/data/market-data.json");
  const profilePath = resolve("public/data/company-profiles.json");
  const existing = await existingMarketData(outputPath);
  const existingProfiles = await existingCompanyProfiles(profilePath);
  const [historySnapshots, fetchedIntraday, companyProfiles] = await Promise.all([
    fetchHistorySnapshots(symbols, 8),
    fetchIntradayHistories(intradaySymbols, 8),
    fetchCompanyProfiles(currentSymbols, existingProfiles, 4),
  ]);
  const fetchedHistories = Object.fromEntries(symbols.map((symbol) => [symbol, historySnapshots[symbol]?.points ?? []]));
  const confirmedHistories = merge(existing.histories ?? await existingHistories(outputPath), fetchedHistories, symbols);
  const fallbackHistories = Object.fromEntries(intradaySymbols.map((symbol) => {
    const fallback = validatedRegularCloseFallback(historySnapshots[symbol] ?? { points: [] }, fetchedIntraday[symbol] ?? []);
    return [symbol, fallback ? [fallback] : []];
  }));
  let histories = merge(confirmedHistories, fallbackHistories, symbols);
  const intraday = mergeIntraday(existing.intraday ?? {}, fetchedIntraday, intradaySymbols);
  const latestPrices = Object.fromEntries(intradaySymbols.flatMap((symbol) => {
    const point = fetchedIntraday[symbol]?.at(-1);
    return point ? [[symbol, { price: point.close, asOf: point.timestamp }]] : [];
  }));
  const oos = await optionalJson<ForwardOosResult>(resolve("public/data/oos-performance.json"));
  const frozen = await optionalJson<{ backtest?: BacktestResult }>(resolve("public/data/backtest-frozen.json"));
  const nportOperations = await optionalJson<NportOperations>(resolve("data/nport-operations.json"));

  // QQQ is the strategy clock. Before advancing it to a newly closed session,
  // require every price needed for that session's execution/risk transition.
  // This prevents a partial update from silently valuing a held name at a stale close.
  const candidateDate = histories.QQQ?.at(-1)?.date;
  let warning: string | undefined;
  if (candidateDate) {
    const priorHistories = Object.fromEntries(Object.entries(histories).map(([symbol, points]) => [symbol, points.filter((point) => point.date < candidateDate)]));
    const priorState = runStrategySimulation({ histories: priorHistories, universeHistory }).state;
    const monthlyUniverse = universeHistory.find((month) => month.asOf === candidateDate);
    const required = new Set<string>(["QQQ", ...priorState.currentPositions.map((position) => position.symbol)]);
    if (priorState.nextAction.executionDate === candidateDate) {
      for (const symbol of priorState.nextAction.symbols) required.add(symbol);
    }
    if (monthlyUniverse) {
      for (const member of monthlyUniverse.symbols) required.add(member.symbol);
    }
    const missing = [...required].filter((symbol) => !histories[symbol]?.some((point) => point.date === candidateDate));
    if (missing.length) {
      histories = { ...histories, QQQ: histories.QQQ.filter((point) => point.date !== candidateDate) };
      warning = `${candidateDate} daily close was not activated because required prices are incomplete: ${missing.join(", ")}`;
    }
  }

  const latestObservedDate = [
    historySnapshots.QQQ?.pendingLatest?.date,
    fetchedIntraday.QQQ?.at(-1)?.timestamp.slice(0, 10),
  ].filter((value): value is string => Boolean(value)).sort().at(-1);
  const activatedDate = histories.QQQ?.at(-1)?.date;
  if (latestObservedDate && (!activatedDate || latestObservedDate > activatedDate)) {
    warning = warning ?? `${latestObservedDate} Yahoo daily close is incomplete and the validated regular-close fallback did not pass.`;
  }
  const requireLatestClose = ["1", "true"].includes(process.env.REQUIRE_LATEST_DAILY_CLOSE ?? "");
  if (requireLatestClose) {
    const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(new Date()).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
    const todayEt = `${parts.year}-${parts.month}-${parts.day}`;
    const expectedSession = previousUsTradingSession(todayEt);
    if (!activatedDate || activatedDate < expectedSession) {
      warning = warning ?? `Latest activated daily close is ${activatedDate ?? "none"}; expected at least ${expectedSession} before the next US open.`;
    }
  }
  if (warning) console.warn(`MARKET_DATA_NOT_READY ${warning}`);
  if (warning && requireLatestClose) throw new Error(warning);

  const dashboard = buildDashboardPayload(histories, universeHistory, "live", { oos, frozenBacktest: frozen?.backtest, nportOperations, latestPrices });
  if (warning) dashboard.warning = warning;
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify({ generatedAt: dashboard.generatedAt, histories, intraday, dashboard })}\n`);
  await writeFile(resolve("public/data/dashboard.json"), `${JSON.stringify({ dashboard })}\n`);
  await writeFile(resolve("public/data/live-state.json"), `${JSON.stringify(dashboard.liveState)}\n`);
  await writeFile(profilePath, `${JSON.stringify({ generatedAt: dashboard.generatedAt, profiles: companyProfiles })}\n`);
  console.log(`Saved ${outputPath}; signal ${dashboard.currentSignal?.signalDate ?? "none"}; state ${dashboard.liveState.state}; company profiles ${currentSymbols.length}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
