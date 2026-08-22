import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { DEFAULT_STRATEGY, TICKERS } from "../src/lib/config";
import { buildDashboard } from "../src/lib/momentum";
import type { PricePoint } from "../src/lib/types";
import { fetchHistories, fetchIntradayHistories } from "../src/lib/yahoo";

type MarketDataFile = {
  histories?: Record<string, PricePoint[]>;
};

type AtlasPosition = { x: number; y: number; z: number };

const INDUSTRY_CENTERS: Record<string, [number, number, number]> = {
  "Nasdaq Beta": [0.84, -0.48, 0.58],
  "AI Semi": [0.62, 0.28, 0.42],
  "AI Infrastructure": [0.5, 0.08, 0.5],
  "AI Application": [0.48, -0.08, 0.28],
  "AI Fintech": [0.32, -0.24, 0.16],
  Robotics: [0.2, 0.48, -0.26],
  "Optical Networking": [0.67, 0.1, 0.32],
  Space: [0.02, 0.7, -0.42],
  Quantum: [-0.16, 0.56, -0.5],
  Defense: [-0.68, 0.3, 0.14],
  "Defense AI": [-0.46, 0.17, 0.22],
  Cybersecurity: [-0.38, 0.08, 0.26],
  Nuclear: [-0.58, -0.55, 0.28],
  "Energy Infrastructure": [-0.38, -0.46, 0.18],
  "Critical Minerals": [-0.74, -0.35, 0.42],
  Crypto: [0.02, -0.33, -0.7],
};

function buildAtlasPositions() {
  return Object.fromEntries(TICKERS.map((ticker, index) => {
    const [x, y, z] = INDUSTRY_CENTERS[ticker.genre] ?? [0, 0, 0];
    const angle = index * 2.399963229728653;
    return [ticker.symbol, {
      x: x + Math.cos(angle) * 0.085,
      y: y + Math.sin(angle) * 0.085,
      z: z + Math.cos(angle * 1.7) * 0.085,
    } satisfies AtlasPosition];
  }));
}

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
  const atlasPositions = buildAtlasPositions();
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
    JSON.stringify({ generatedAt, histories, intraday, atlas: { method: "industry-taxonomy", positions: atlasPositions }, dashboard }),
    "utf8",
  );

  console.log(`Saved ${outputPath}`);
  console.log(`As of ${dashboard.asOf}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
