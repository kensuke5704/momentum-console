export {};

const USER_AGENT = process.env.SEC_USER_AGENT ?? "MomentumConsole/2.0 kensuke5704@users.noreply.github.com";
const BASE = "https://www.sec.gov/files/dera/data/form-n-port-data-sets";

async function main() {
  const results: Array<Record<string, unknown>> = [];
  for (let year = 2020; year <= 2026; year++) {
    for (let q = 1; q <= 4; q++) {
      if (year === 2026 && q > 2) break;
      const quarter = `${year}q${q}`;
      const url = `${BASE}/${quarter}_nport.zip`;
      const response = await fetch(url, {
        method: "HEAD",
        headers: { "User-Agent": USER_AGENT, Accept: "application/zip,*/*" },
        signal: AbortSignal.timeout(30_000),
      });
      results.push({
        quarter,
        status: response.status,
        lastModified: response.headers.get("last-modified"),
        etag: response.headers.get("etag"),
        date: response.headers.get("date"),
        contentLength: response.headers.get("content-length"),
      });
    }
  }
  console.log(`NPORT_DATASET_AVAILABILITY=${JSON.stringify(results)}`);
  if (results.some((row) => row.status !== 200 || !row.lastModified)) process.exitCode = 1;
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
