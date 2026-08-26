import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { NportFiling, UniverseMonth } from "../src/lib/types";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";

const START = process.env.PARITY_START ?? "2026-04-01";
const SIGNAL_MONTH = process.env.PARITY_SIGNAL_MONTH ?? "2026-05";
const SIGNAL_DATE = process.env.PARITY_SIGNAL_DATE ?? "2026-05-29";

async function main() {
  const quarterly = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] };
  const live = JSON.parse(await readFile(resolve("data/sec-nport/live-filings.json"), "utf8")) as { filings: NportFiling[] };
  const history = JSON.parse(await readFile(resolve("public/data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const truth = history.history.find((m) => m.signalMonth === SIGNAL_MONTH && m.asOf === SIGNAL_DATE);
  if (!truth) throw new Error(`truth Universe not found for ${SIGNAL_MONTH} ${SIGNAL_DATE}`);
  const previous = history.history.filter((m) => m.asOf < SIGNAL_DATE).at(-2) ?? null;
  const seed = quarterly.filings.filter((f) => f.filingDate < START);
  const direct = live.filings.filter((f) => f.filingDate >= START && f.filingDate <= SIGNAL_DATE);
  const merged = new Map<string, NportFiling>();
  for (const f of seed) merged.set(f.accession, f);
  for (const f of direct) merged.set(f.accession, f);
  const rebuilt = buildPointInTimeUniverse([...merged.values()], SIGNAL_MONTH, SIGNAL_DATE, previous);
  const truthSymbols = truth.symbols.map((x) => x.symbol), rebuiltSymbols = rebuilt.symbols.map((x) => x.symbol);
  const truthSet = new Set(truthSymbols), rebuiltSet = new Set(rebuiltSymbols);
  const added = rebuiltSymbols.filter((x) => !truthSet.has(x));
  const missing = truthSymbols.filter((x) => !rebuiltSet.has(x));
  const sourceTruth = new Set(truth.sourceFilings.map((x) => x.accession));
  const sourceRebuilt = new Set(rebuilt.sourceFilings.map((x) => x.accession));
  const missingSources = [...sourceTruth].filter((x) => !sourceRebuilt.has(x));
  const extraSources = [...sourceRebuilt].filter((x) => !sourceTruth.has(x));
  const intersection = truthSymbols.filter((x) => rebuiltSet.has(x)).length;
  const union = new Set([...truthSymbols, ...rebuiltSymbols]).size;
  const result = {
    generatedAt: new Date().toISOString(), start: START, signalMonth: SIGNAL_MONTH, signalDate: SIGNAL_DATE,
    seedQuarterlyFilings: seed.length, directEdgarFilings: direct.length,
    truthSourceFilings: truth.sourceFilings.length, rebuiltSourceFilings: rebuilt.sourceFilings.length,
    top80Jaccard: union ? intersection / union : 1,
    identicalTop80: added.length === 0 && missing.length === 0,
    sourceAccessionRecall: sourceTruth.size ? (sourceTruth.size - missingSources.length) / sourceTruth.size : 1,
    added, missing, missingSources, extraSources,
  };
  await mkdir(resolve("data/research/live-nport-ingestion"), { recursive: true });
  await writeFile(resolve("data/research/live-nport-ingestion/historical-parity.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log("HISTORICAL_LIVE_PARITY=" + JSON.stringify(result));
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
