import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { DEFAULT_STRATEGY, TICKERS } from "../src/lib/config";
import { buildDashboard } from "../src/lib/momentum";
import type { PricePoint } from "../src/lib/types";
import { fetchHistories, fetchIntradayHistories } from "../src/lib/yahoo";

type MarketDataFile = {
  histories?: Record<string, PricePoint[]>;
};

function mergeHistories(
  existing: Record<string, PricePoint[]>,
  fetched: Record<string, PricePoint[]>,
  symbols: string[],
) {
  const merged: Record<string, PricePoint[]> = {};

  symbols.forEach((symbol) => {
    const byDate = new Map<string, PricePoint>();
    (existing[symbol] ?? []).forEach((point) => byDate.set(point.date, point));
    (fetched[symbol] ?? []).forEach((point) => byDate.set(point.date, point));
    merged[symbol] = [...byDate.values()].sort((a, b) =>
      a.date.localeCompare(b.date),
    );
  });

  return merged;
}

async function readExistingHistories(outputPath: string) {
  try {
    const body = JSON.parse(await readFile(outputPath, "utf8")) as MarketDataFile;
    return body.histories ?? {};
  } catch {
    return {};
  }
}

async function main() {
  const symbols = [
    ...new Set([...TICKERS.map((ticker) => ticker.symbol), "JPY=X"]),
  ];
  console.log(`Fetching ${symbols.length} symbols...`);

  const fetchedHistories = await fetchHistories(symbols);
  const intraday = await fetchIntradayHistories(symbols);
  const outputPath = resolve("public/data/market-data.json");
  const existingHistories = await readExistingHistories(outputPath);
  const histories = mergeHistories(existingHistories, fetchedHistories, symbols);
  const usdJpyPoints = histories["JPY=X"] ?? [];
  const latestUsdJpy = usdJpyPoints.at(-1)?.close;
  const strategy = {
    ...DEFAULT_STRATEGY,
    usdJpy:
      typeof latestUsdJpy === "number" && Number.isFinite(latestUsdJpy)
        ? latestUsdJpy
        : DEFAULT_STRATEGY.usdJpy,
  };
  const dashboard = buildDashboard(histories, TICKERS, strategy);
  const generatedAt = new Date().toISOString();
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(
    outputPath,
    JSON.stringify({ generatedAt, histories, intraday, dashboard }),
    "utf8",
  );

  console.log(`Saved ${outputPath}`);
  console.log(`As of ${dashboard.asOf}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
