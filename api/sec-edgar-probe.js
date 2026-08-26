const USER_AGENT = "MomentumConsole/2.0 kensuke5704@users.noreply.github.com";

const TARGETS = [
  "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR3/master.20260731.idx",
  "https://www.sec.gov/Archives/edgar/data/850027/000085002726000015/primary_doc.xml",
];

module.exports = async function handler(_req, res) {
  const results = [];
  for (const url of TARGETS) {
    try {
      const response = await fetch(url, {
        headers: {
          "User-Agent": USER_AGENT,
          "Accept-Encoding": "gzip, deflate",
          Host: "www.sec.gov",
          Accept: "text/plain,application/xml,*/*",
        },
        redirect: "follow",
        signal: AbortSignal.timeout(20_000),
      });
      const body = await response.text();
      results.push({
        url,
        status: response.status,
        ok: response.ok,
        contentType: response.headers.get("content-type"),
        length: body.length,
        blocked: /Undeclared Automated Tool|Request Rate Threshold/i.test(body),
        containsNport: /NPORT-P/i.test(body),
      });
    } catch (error) {
      results.push({ url, status: 0, ok: false, error: String(error) });
    }
  }
  const ok = results.every((result) => result.ok === true);
  res.status(ok ? 200 : 503).json({ generatedAt: new Date().toISOString(), runtime: "vercel", ok, results });
};
