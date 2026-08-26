import { copyFile, mkdir, mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { spawn } from "node:child_process";
import { basename, join, resolve } from "node:path";
import { tmpdir } from "node:os";

const REQUIRED_TABLES = [
  "SUBMISSION.tsv",
  "FUND_REPORTED_INFO.tsv",
  "FUND_REPORTED_HOLDING.tsv",
  "IDENTIFIERS.tsv",
] as const;

async function run(command: string, args: string[], env: NodeJS.ProcessEnv = process.env) {
  await new Promise<void>((resolvePromise, reject) => {
    const child = spawn(command, args, { stdio: "inherit", env });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolvePromise() : reject(new Error(`${command} ${args.join(" ")} exited with ${code}`)));
  });
}

async function capture(command: string, args: string[]): Promise<string> {
  return await new Promise<string>((resolvePromise, reject) => {
    const child = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolvePromise(stdout) : reject(new Error(`${command} ${args.join(" ")} exited with ${code}: ${stderr.trim()}`)));
  });
}

function quarterFromName(path: string): string {
  const match = /(?:^|[^0-9])(20\d{2})q([1-4])(?:_nport)?\.zip$/i.exec(basename(path));
  if (!match) throw new Error("ZIP filename must identify the SEC quarter, e.g. 2026q3_nport.zip");
  return `${match[1]}q${match[2]}`.toLowerCase();
}

async function validateZip(path: string) {
  const info = await stat(path);
  if (!info.isFile() || info.size < 10_000) throw new Error(`Invalid or unexpectedly small ZIP: ${path}`);
  const listing = (await capture("unzip", ["-Z1", path])).split(/\r?\n/).filter(Boolean);
  for (const table of REQUIRED_TABLES) {
    if (!listing.includes(table)) throw new Error(`Missing required table ${table}`);
  }
  for (const table of REQUIRED_TABLES) {
    const header = (await capture("unzip", ["-p", path, table])).split(/\r?\n/, 1)[0]?.trim();
    if (!header || !header.includes("ACCESSION_NUMBER")) throw new Error(`${table}: invalid header`);
  }
}

async function currentProcessedQuarters(): Promise<string[]> {
  try {
    const parsed = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { quarters?: string[] };
    return parsed.quarters ?? [];
  } catch {
    return [];
  }
}

async function main() {
  const raw = process.argv[2];
  if (!raw) throw new Error("Usage: npm run import:nport -- /path/to/2026q3_nport.zip");
  const source = resolve(raw);
  const quarter = quarterFromName(source);
  await validateZip(source);

  const processed = await currentProcessedQuarters();
  if (processed.includes(quarter)) {
    throw new Error(`${quarter} is already recorded in data/sec-nport/filings.json. Refusing to overwrite an audited quarter automatically.`);
  }

  const cache = await mkdtemp(join(tmpdir(), "momentum-console-nport-import-"));
  try {
    const cachedZip = join(cache, `${quarter}_nport.zip`);
    await copyFile(source, cachedZip);
    console.log(`Validated ${basename(source)} as SEC N-PORT ${quarter}`);

    const env = {
      ...process.env,
      NPORT_CACHE_DIR: cache,
      NPORT_START_QUARTER: quarter,
      NPORT_END_QUARTER: quarter,
      KEEP_NPORT_ZIPS: "1",
    };

    await run("npm", ["run", "sync:sec"], env);

    const after = await currentProcessedQuarters();
    if (!after.includes(quarter)) throw new Error(`${quarter} was not recorded after sync:sec`);

    await run("npm", ["run", "sync:universe"]);
    await run("npm", ["run", "sync:atlas"]);
    await run("npm", ["run", "sync:data"]);
    await run("npm", ["run", "sync:oos"]);
    await run("npm", ["run", "check"]);

    console.log(`MANUAL_NPORT_IMPORT_OK quarter=${quarter}`);
    console.log("Review git diff before committing. This command never commits or pushes automatically.");
  } finally {
    await rm(cache, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
