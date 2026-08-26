import test from "node:test";
import assert from "node:assert/strict";
import { parseNportXml } from "../src/lib/universe/edgar-live";

test("parseNportXml extracts US corporate equity holdings", () => {
  const xml = `<?xml version="1.0"?><edgarSubmission><headerData><filerInfo><seriesClassInfo><seriesId>S0001</seriesId></seriesClassInfo></filerInfo></headerData><formData><genInfo><seriesName>Example Growth ETF</seriesName><seriesId>S0001</seriesId><repPdDate>2026-06-30</repPdDate></genInfo><invstOrSecs><invstOrSec><name>NVIDIA Corp</name><identifiers><ticker value="NVDA"/></identifiers><pctVal>8.5</pctVal><assetCat>EC</assetCat><issuerCat>CORP</issuerCat><invCountry>US</invCountry></invstOrSec><invstOrSec><name>Bond</name><identifiers><ticker value="BOND"/></identifiers><pctVal>5</pctVal><assetCat>DBT</assetCat><issuerCat>CORP</issuerCat><invCountry>US</invCountry></invstOrSec></invstOrSecs></formData></edgarSubmission>`;
  const parsed = parseNportXml(xml, "0000000000-26-000001", "2026-08-01");
  assert.ok(parsed);
  assert.equal(parsed.seriesId, "S0001");
  assert.equal(parsed.seriesName, "Example Growth ETF");
  assert.equal(parsed.reportDate, "2026-06-30");
  assert.deepEqual(parsed.holdings, [{ symbol: "NVDA", issuerName: "NVIDIA Corp", weight: 8.5 }]);
});
