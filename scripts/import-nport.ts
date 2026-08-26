import { spawn } from "node:child_process";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { gzipSync, gunzipSync } from "node:zlib";
import type { DashboardPayload, ForwardOosResult, NportFiling, UniverseMonth } from "../src/lib/types";
import { parseQuarterlyNportZip, quarterForDate } from "../src/lib/universe/nport-quarterly";

const OUTPUT = resolve("data/sec-nport/filings.json");
const BOOTSTRAP = resolve("data/sec-nport/bootstrap.json.gz");

function run(command: string, args: string[]): Promise<void> {
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, { stdio: "inherit", env: process.env });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolveRun() : reject(new Error(`${command} ${args.join(" ")} exited with ${code}`)));
  });
}

function quarterRange(start: string, end: string): string[] {
  const parse = (value: string) => ({ year: Number(value.slice(0, 4)), quarter: Number(value.at(-1)) });
  const first = parse(start), last = parse(end), output: string[] = [];
  for (let year = first.year; year <= last.year; year++) for (let quarter = 1; quarter <= 4; quarter++) {
    if (year === first.year && quarter < first.quarter) continue;
    if (year === last.year && quarter > last.quarter) continue;
    output.push(`${year}q${quarter}`);
  }
  return output;
}

async function loadExisting(): Promise<{ filings: NportFiling[]; quarters: string[] }> {
  try {
    const existing = JSON.parse(await readFile(OUTPUT, "utf8")) as { filings?: NportFiling[]; quarters?: string[] };
    return { filings: existing.filings ?? [], quarters: existing.quarters ?? [] };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    const bootstrap = JSON.parse(gunzipSync(await readFile(BOOTSTRAP)).toString("utf8")) as { snapshots?: NportFiling[]; startQuarter?: string; endQuarter?: string };
    const quarters = bootstrap.startQuarter && bootstrap.endQuarter ? quarterRange(bootstrap.startQuarter, bootstrap.endQuarter) : [];
    return { filings: bootstrap.snapshots ?? [], quarters };
  }
}

async function currentUniverseSymbols(): Promise<string[]> {
  try {
    const payload = JSON.parse(await readFile(resolve("public/data/universe-current.json"), "utf8")) as { current?: UniverseMonth | null };
    return payload.current?.symbols.map((member) => member.symbol) ?? [];
  } catch { return []; }
}

async function validateGeneratedOutputs(): Promise<{ dashboard: DashboardPayload; current: UniverseMonth }> {
  const universe = JSON.parse(await readFile(resolve("public/data/universe-current.json"), "utf8")) as { current?: UniverseMonth | null };
  const dashboardFile = JSON.parse(await readFile(resolve("public/data/dashboard.json"), "utf8")) as { dashboard: DashboardPayload };
  const oos = JSON.parse(await readFile(resolve("public/data/oos-performance.json"), "utf8")) as ForwardOosResult;
  const current = universe.current;
  const dashboard = dashboardFile.dashboard;
  if (!current || current.symbols.length !== dashboard.config.universe.size) throw new Error("Generated current Universe is missing or is not Top 80");
  if (dashboard.currentUniverse?.asOf !== current.asOf || dashboard.currentUniverse.signalMonth !== current.signalMonth) throw new Error("Dashboard and Universe as-of values are inconsistent");
  if (dashboard.currentSignal?.selectedSymbols.length && dashboard.currentSignal.selectedSymbols.some((symbol) => !current.symbols.some((member) => member.symbol === symbol))) {
    throw new Error("Generated Top2 contains a symbol outside the current Universe");
  }
  if ((dashboard.currentSignal?.selectedSymbols.length ?? 0) > dashboard.config.selection.topN) throw new Error("Generated selection exceeds configured TopN");
  if (oos.strategyId !== dashboard.config.strategyId) throw new Error("OOS and Dashboard strategy IDs are inconsistent");
  return { dashboard, current };
}

async function main() {
  const zipPath = process.argv[2];
  if (!zipPath) throw new Error("Usage: npm run import:nport -- /absolute/path/YYYYqN_nport.zip");
  const beforeSymbols = await currentUniverseSymbols();
  const parsed = await parseQuarterlyNportZip(resolve(zipPath));
  const existing = await loadExisting();
  const retained = existing.filings.filter((filing) => quarterForDate(filing.filingDate) !== parsed.quarter);
  const merged = new Map(retained.map((filing) => [filing.accession, filing]));
  for (const filing of parsed.filings) merged.set(filing.accession, filing);
  const filings = [...merged.values()].sort((a, b) => a.filingDate.localeCompare(b.filingDate) || a.seriesId.localeCompare(b.seriesId));
  const quarters = [...new Set([...existing.quarters.filter((quarter) => quarter !== parsed.quarter), parsed.quarter])].sort();
  const payload = {
    generatedAt: new Date().toISOString(),
    source: "SEC Form N-PORT quarterly public datasets — manually supplied official ZIP",
    quarters,
    filings,
  };
  await mkdir(resolve("data/sec-nport"), { recursive: true });
  const temporary = `${OUTPUT}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(payload)}\n`);
  await rename(temporary, OUTPUT);
  const bootstrap = {
    generatedAt: payload.generatedAt,
    source: payload.source,
    startQuarter: quarters.at(0),
    endQuarter: quarters.at(-1),
    snapshots: filings,
  };
  const bootstrapTemporary = `${BOOTSTRAP}.${process.pid}.tmp`;
  await writeFile(bootstrapTemporary, gzipSync(JSON.stringify(bootstrap), { level: 9 }));
  await rename(bootstrapTemporary, BOOTSTRAP);
  console.log(`Validated ${parsed.quarter}: ${parsed.zipBytes} bytes, sha256=${parsed.sha256}, ${parsed.submissions} submissions, ${parsed.filings.length} eligible ETF filings`);

  for (const script of ["sync:universe", "sync:atlas", "sync:data", "sync:oos", "check"]) await run("npm", ["run", script]);
  await run("git", ["diff", "--quiet", "--", "src/lib/config.ts", "src/lib/strategy"]);

  const { dashboard, current } = await validateGeneratedOutputs();
  const afterSymbols = current.symbols.map((member) => member.symbol);
  const before = new Set(beforeSymbols), after = new Set(afterSymbols);
  const added = afterSymbols.filter((symbol) => !before.has(symbol));
  const removed = beforeSymbols.filter((symbol) => !after.has(symbol));
  const top2 = dashboard.currentSignal?.selectedSymbols ?? [];
  console.log(`MANUAL_NPORT_UNIVERSE added=${added.join(",") || "none"} removed=${removed.join(",") || "none"}`);
  console.log(`MANUAL_NPORT_TOP2 symbols=${top2.join(",") || "none"}`);
  console.log(`MANUAL_NPORT_IMPORT_OK quarter=${parsed.quarter} filings=${parsed.filings.length}`);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
