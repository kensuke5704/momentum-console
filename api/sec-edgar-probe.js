const USER_AGENT = "MomentumConsole/2.0 kensuke5704@users.noreply.github.com";

const quarters = [];
for (let year = 2020; year <= 2026; year++) {
  for (let q = 1; q <= 4; q++) {
    if (year === 2026 && q > 2) break;
    quarters.push(`${year}q${q}`);
  }
}

module.exports = async function handler(_req, res) {
  const results = [];
  for (const quarter of quarters) {
    const url = `https://www.sec.gov/files/dera/data/form-n-port-data-sets/${quarter}_nport.zip`;
    try {
      const response = await fetch(url, {
        method: "HEAD",
        headers: {
          "User-Agent": USER_AGENT,
          Accept: "application/zip,*/*",
          "Accept-Encoding": "gzip, deflate",
        },
        redirect: "follow",
        signal: AbortSignal.timeout(20_000),
      });
      results.push({
        quarter,
        url,
        status: response.status,
        ok: response.ok,
        lastModified: response.headers.get("last-modified"),
        etag: response.headers.get("etag"),
        contentLength: response.headers.get("content-length"),
        date: response.headers.get("date"),
      });
    } catch (error) {
      results.push({ quarter, url, status: 0, ok: false, error: String(error) });
    }
  }
  const ok = results.every((result) => result.ok === true && result.lastModified);
  res.status(ok ? 200 : 503).json({ generatedAt: new Date().toISOString(), runtime: "vercel", ok, results });
};
