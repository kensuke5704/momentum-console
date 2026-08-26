import test from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { parseQuarterlyNportZip, quarterForDate, quarterFromZipName, validateRequiredHeaders } from "../src/lib/universe/nport-quarterly";

const execFileAsync = promisify(execFile);

test("manual N-PORT import accepts only the official quarterly filename pattern", () => {
  assert.equal(quarterFromZipName("/tmp/2026q2_nport.zip"), "2026q2");
  assert.throws(() => quarterFromZipName("/tmp/nport-latest.zip"), /YYYYqN_nport/);
});

test("manual N-PORT import derives the calendar quarter from filing date", () => {
  assert.equal(quarterForDate("2026-01-02"), "2026q1");
  assert.equal(quarterForDate("2026-06-30"), "2026q2");
  assert.equal(quarterForDate("2026-12-31"), "2026q4");
});

test("manual N-PORT import rejects missing required TSV headers", () => {
  assert.doesNotThrow(() => validateRequiredHeaders("SUBMISSION", ["ACCESSION_NUMBER", "REPORT_DATE", "FILING_DATE"]));
  assert.throws(() => validateRequiredHeaders("SUBMISSION", ["ACCESSION_NUMBER", "REPORT_DATE"]), /FILING_DATE/);
});

test("manual N-PORT import parses a structurally valid quarterly ZIP", async () => {
  const directory = await mkdtemp(join(tmpdir(), "nport-quarterly-test-"));
  try {
    const files: Record<string, string> = {
      "SUBMISSION.tsv": "ACCESSION_NUMBER\tREPORT_DATE\tFILING_DATE\n0000000000-26-000001\t30-JUN-2026\t15-MAY-2026\n",
      "FUND_REPORTED_INFO.tsv": "ACCESSION_NUMBER\tSERIES_NAME\tSERIES_ID\n0000000000-26-000001\tExample Growth ETF\tS0001\n",
      "FUND_REPORTED_HOLDING.tsv": "ACCESSION_NUMBER\tHOLDING_ID\tASSET_CAT\tINVESTMENT_COUNTRY\tISSUER_TYPE\tISSUER_NAME\tPERCENTAGE\n0000000000-26-000001\tH1\tEC\tUS\tCORP\tNVIDIA Corp\t8.5\n",
      "IDENTIFIERS.tsv": "HOLDING_ID\tIDENTIFIER_TICKER\nH1\tNVDA\n",
    };
    await Promise.all(Object.entries(files).map(([name, content]) => writeFile(join(directory, name), content)));
    const zip = join(directory, "2026q2_nport.zip");
    await execFileAsync("zip", ["-q", zip, ...Object.keys(files)], { cwd: directory });
    const parsed = await parseQuarterlyNportZip(zip);
    assert.equal(parsed.quarter, "2026q2");
    assert.equal(parsed.submissions, 1);
    assert.equal(parsed.filings.length, 1);
    assert.equal(parsed.filings[0].holdings[0].symbol, "NVDA");
    assert.match(parsed.sha256, /^[a-f0-9]{64}$/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
