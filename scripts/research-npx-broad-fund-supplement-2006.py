#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "research" / "npx-security-master-broad-fund-supplement-2006.json"

spec = importlib.util.spec_from_file_location("pilot", ROOT / "scripts" / "research-npx-security-master-2006.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)

# Pre-fixed from SEC-indexed 2006 Form N-PX filings for broad/large fund complexes.
# Selection is by registrant/fund family only; it does not use N-Q unmapped holdings or strategy returns.
SOURCES = [
    {"family": "Fidelity", "cik": "35348", "url": "https://www.sec.gov/Archives/edgar/data/35348/0000023355-06-000076.txt"},
    {"family": "Vanguard", "cik": "826473", "url": "https://www.sec.gov/Archives/edgar/data/826473/000093247106001390/0000932471-06-001390.txt"},
    {"family": "Vanguard", "cik": "68138", "url": "https://www.sec.gov/Archives/edgar/data/68138/000093247106001404/0000932471-06-001404.txt"},
    {"family": "Eaton Vance", "cik": "745463", "url": "https://www.sec.gov/Archives/edgar/data/745463/000127163106000230/0001271631-06-000230.txt"},
    {"family": "Oppenheimer", "cik": "752737", "url": "https://www.sec.gov/Archives/edgar/data/752737/000075273706000008/vabalancedtohighincome.htm"},
    {"family": "Putnam", "cik": "81247", "url": "https://www.sec.gov/Archives/edgar/data/81247/000092881606000935/a_convinc.htm"},
    {"family": "ING", "cik": "916403", "url": "https://www.sec.gov/Archives/edgar/data/916403/000119312506182493/dnpx.htm"},
    {"family": "RS Investments", "cik": "814232", "url": "https://www.sec.gov/Archives/edgar/data/814232/000081423206000006/npx06final.htm"},
    {"family": "UBS", "cik": "1039949", "url": "https://www.sec.gov/Archives/edgar/data/1039949/000110465906056698/a06-17250_18npx.htm"},
    {"family": "Salomon Brothers", "cik": "202385", "url": "https://www.sec.gov/Archives/edgar/data/202385/000119312506181203/dnpx.htm"},
    {"family": "Wilshire", "cik": "1026708", "url": "https://www.sec.gov/Archives/edgar/data/1026708/000119312506183510/dnpx.htm"},
]


def main() -> None:
    rows = []
    source_results = []
    for i, source in enumerate(SOURCES, 1):
        try:
            text = pilot.fetch_text(source["url"])
            records = pilot.parse_records(text)
            paired = [r for r in records if r.get("ticker") and r.get("securityId")]
            source_results.append({**source, "records": len(records), "pairedRecords": len(paired), "fetchOk": True})
            for r in paired:
                rows.append({
                    "issuer": r["issuer"],
                    "normalizedIssuer": "",
                    "ticker": r.get("ticker"),
                    "securityId": r.get("securityId"),
                    "meetingDateRaw": r.get("meetingDateRaw"),
                    "sourceFilingDate": "2006",
                    "sourceCik": source["cik"],
                    "sourceCompany": source["family"],
                    "sourceFilename": source["url"],
                    "sourceRule": "pre-fixed broad-fund-family supplement",
                })
            print(f"{i}/{len(SOURCES)} {source['family']} records={len(records)} paired={len(paired)}", flush=True)
        except Exception as exc:
            source_results.append({**source, "fetchOk": False, "error": repr(exc)})
            print(f"{i}/{len(SOURCES)} FAIL {source['family']} {exc!r}", flush=True)
        if i < len(SOURCES):
            time.sleep(1.0)

    # Reuse exactly the normalization rule from the expanded master builder.
    bspec = importlib.util.spec_from_file_location("builder", ROOT / "scripts" / "research-npx-security-master-build-2006.py")
    builder = importlib.util.module_from_spec(bspec)
    bspec.loader.exec_module(builder)
    for row in rows:
        row["normalizedIssuer"] = builder.normalize_issuer(row["issuer"])

    unique = {}
    for row in rows:
        key = (row["normalizedIssuer"], row.get("ticker"), row.get("securityId"))
        unique.setdefault(key, row)
    rows = list(unique.values())

    out = {
        "year": 2006,
        "purpose": "Broad-fund-family N-PX supplement for structural issuer/ticker/security-id mapping; no N-Q unmatched-name or return-based source selection.",
        "sourceRule": "Fixed 2006 SEC N-PX filings from broad/large fund families discovered independently of N-Q mapping misses.",
        "sourceCount": len(SOURCES),
        "fetchSuccess": sum(1 for x in source_results if x.get("fetchOk")),
        "pairedRecords": len(rows),
        "uniqueTickers": len({r["ticker"] for r in rows if r.get("ticker")}),
        "uniqueSecurityIds": len({r["securityId"] for r in rows if r.get("securityId")}),
        "records": rows,
        "sourceResults": source_results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k not in {"records", "sourceResults"}}), flush=True)


if __name__ == "__main__":
    main()
