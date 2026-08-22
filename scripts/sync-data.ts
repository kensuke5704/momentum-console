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

const INDUSTRY_AXES: Record<string, [number, number, number]> = {
  "ai-compute": [0.78, 0.34, 0.45],
  "data-center": [0.48, 0.08, 0.52],
  networking: [0.62, -0.02, 0.34],
  software: [0.3, -0.14, 0.24],
  fintech: [0.12, -0.3, 0.04],
  robotics: [0.18, 0.5, -0.24],
  space: [-0.04, 0.72, -0.44],
  quantum: [-0.2, 0.52, -0.5],
  defense: [-0.72, 0.32, 0.14],
  cybersecurity: [-0.4, 0.08, 0.28],
  nuclear: [-0.6, -0.58, 0.3],
  "power-grid": [-0.36, -0.44, 0.18],
  materials: [-0.76, -0.34, 0.42],
  crypto: [0.02, -0.34, -0.7],
  "nasdaq-index": [0.86, -0.5, 0.6],
};

const INDUSTRY_TAGS: Record<string, Record<string, number>> = {
  TQQQ: { "nasdaq-index": 1 }, QQQ: { "nasdaq-index": 1 },
  SOXL: { "ai-compute": 0.9, "data-center": 0.35 }, NVDL: { "ai-compute": 0.9, "data-center": 0.7 }, NVDA: { "ai-compute": 1, "data-center": 0.8, networking: 0.25 }, MU: { "ai-compute": 0.55, "data-center": 0.65 },
  LITE: { networking: 1, "data-center": 0.7 }, FN: { networking: 1, "data-center": 0.7 }, VRT: { "data-center": 1, "power-grid": 0.45 },
  DDOG: { software: 0.85, "data-center": 0.65 }, NET: { networking: 0.7, software: 0.7, cybersecurity: 0.35 }, APP: { software: 1, "ai-compute": 0.35 }, SYM: { robotics: 1, "ai-compute": 0.3 }, SERV: { robotics: 1 },
  UPST: { fintech: 1, "ai-compute": 0.35 }, AFRM: { fintech: 1 },
  RKLB: { space: 1, defense: 0.25 }, LUNR: { space: 1 }, ASTS: { space: 0.8, networking: 0.45 }, IONQ: { quantum: 1, "ai-compute": 0.3 }, QBTS: { quantum: 1, "ai-compute": 0.3 },
  AVAV: { defense: 1, robotics: 0.35 }, KTOS: { defense: 1, robotics: 0.25 }, RCAT: { defense: 0.9, robotics: 0.55 }, PLTR: { defense: 0.75, software: 0.85, "ai-compute": 0.35 }, BBAI: { defense: 0.65, "ai-compute": 0.85, software: 0.45 },
  CRWD: { cybersecurity: 1, software: 0.7 }, PANW: { cybersecurity: 1, software: 0.5 }, S: { cybersecurity: 1, software: 0.4 },
  BE: { nuclear: 0.6, "power-grid": 0.8 }, OKLO: { nuclear: 1 }, LEU: { nuclear: 1, materials: 0.5 }, UUUU: { nuclear: 0.8, materials: 0.8 }, NXE: { nuclear: 0.8, materials: 0.8 }, MP: { materials: 1, "ai-compute": 0.2 }, MOD: { "power-grid": 1 }, PWR: { "power-grid": 1, "data-center": 0.25 }, FIX: { "power-grid": 1, "data-center": 0.4 },
  CLSK: { crypto: 1, "data-center": 0.25 }, MSTR: { crypto: 1, software: 0.2 }, COIN: { crypto: 1, fintech: 0.35 }, RIOT: { crypto: 1, "data-center": 0.2 },
};

function buildAtlasPositions() {
  return Object.fromEntries(TICKERS.map((ticker, index) => {
    const tags = INDUSTRY_TAGS[ticker.symbol] ?? {};
    let x = 0, y = 0, z = 0, total = 0;
    Object.entries(tags).forEach(([tag, weight]) => {
      const axis = INDUSTRY_AXES[tag];
      if (!axis) return;
      x += axis[0] * weight; y += axis[1] * weight; z += axis[2] * weight; total += weight;
    });
    const angle = index * 2.399963229728653;
    return [ticker.symbol, {
      x: x / (total || 1) + Math.cos(angle) * 0.045,
      y: y / (total || 1) + Math.sin(angle) * 0.045,
      z: z / (total || 1) + Math.cos(angle * 1.7) * 0.045,
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
  const atlasHistories = Object.fromEntries(
    TICKERS.map((ticker) => [ticker.symbol, (histories[ticker.symbol] ?? []).slice(-270)]),
  );
  await writeFile(
    resolve("public/data/market-atlas.json"),
    JSON.stringify({ generatedAt, histories: atlasHistories, intraday, atlas: { method: "business-context-tags", positions: atlasPositions } }),
    "utf8",
  );

  console.log(`Saved ${outputPath}`);
  console.log(`As of ${dashboard.asOf}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
