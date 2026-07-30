import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { DEFAULT_STRATEGY, TICKERS } from "../src/lib/config";
import { buildDashboard } from "../src/lib/momentum";
import { fetchHistories } from "../src/lib/yahoo";

async function main() {
  const symbols = [...new Set(TICKERS.map((ticker) => ticker.symbol))];
  console.log(`Fetching ${symbols.length} symbols...`);

  const histories = await fetchHistories(symbols);
  const dashboard = buildDashboard(histories, TICKERS, DEFAULT_STRATEGY);
  const generatedAt = new Date().toISOString();
  const outputPath = resolve("public/data/market-data.json");

  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(
    outputPath,
    JSON.stringify({ generatedAt, histories, dashboard }),
    "utf8",
  );

  console.log(`Saved ${outputPath}`);
  console.log(`As of ${dashboard.asOf}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
