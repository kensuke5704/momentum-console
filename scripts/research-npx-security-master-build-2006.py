#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "research" / "npx-security-master-2006.json"
SAMPLE_COUNT = 24

spec = importlib.util.spec_from_file_location("pilot", ROOT / "scripts" / "research-npx-security-master-2006.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def normalize_issuer(raw: str) -> str:
    s = raw.upper()
    s = re.sub(r"&", " AND ", s)
    s = re.sub(r"\b(INCORPORATED|INCORPORATION)\b", "INC", s)
    s = re.sub(r"\b(CORPORATION|CORPORA?TION)\b", "CORP", s)
    s = re.sub(r"\b(COMPANY)\b", "CO", s)
    s = re.sub(r"\b(LIMITED)\b", "LTD", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return " ".join(s.split())


def deterministic_quantile_sample(filings: list[dict], n: int = SAMPLE_COUNT) -> list[dict]:
    primary = [x for x in filings if x.get("form") == "N-PX"]
    if len(primary) <= n:
        return primary
    positions = [round(i * (len(primary) - 1) / (n - 1)) for i in range(n)]
    out = []
    seen = set()
    for p in positions:
        x = primary[p]
        key = (x["cik"], x["dateFiled"], x["filename"])
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def main() -> None:
    filings = pilot.filing_index_2006()
    samples = deterministic_quantile_sample(filings)
    print(f"samples={len(samples)} from primaryNpx={sum(1 for x in filings if x['form']=='N-PX')}", flush=True)

    source_results = []
    master_rows = []
    for i, x in enumerate(samples, 1):
        try:
            text = pilot.fetch_text(pilot.sec_url(x["filename"]))
            records = pilot.parse_records(text)
            paired = [r for r in records if r.get("ticker") and r.get("securityId")]
            source_results.append({
                **x,
                "bytes": len(text.encode()),
                "records": len(records),
                "pairedRecords": len(paired),
            })
            for r in records:
                master_rows.append({
                    "issuer": r["issuer"],
                    "normalizedIssuer": normalize_issuer(r["issuer"]),
                    "ticker": r.get("ticker"),
                    "securityId": r.get("securityId"),
                    "meetingDateRaw": r.get("meetingDateRaw"),
                    "sourceFilingDate": x["dateFiled"],
                    "sourceCik": x["cik"],
                    "sourceCompany": x["company"],
                    "sourceFilename": x["filename"],
                })
            print(f"{i}/{len(samples)} {x['dateFiled']} {x['company'][:38]} records={len(records)} paired={len(paired)}", flush=True)
        except Exception as e:
            source_results.append({**x, "error": repr(e)})
            print(f"{i}/{len(samples)} FAIL {x['company'][:38]} {e!r}", flush=True)
        if i < len(samples):
            time.sleep(1.0)

    # De-duplicate exact security identities while retaining the earliest observed source.
    unique = {}
    for r in sorted(master_rows, key=lambda z: (z["sourceFilingDate"], z["normalizedIssuer"], z.get("ticker") or "", z.get("securityId") or "")):
        key = (r["normalizedIssuer"], r.get("ticker"), r.get("securityId"))
        unique.setdefault(key, r)
    rows = list(unique.values())

    paired_rows = [r for r in rows if r.get("ticker") and r.get("securityId")]
    by_issuer = defaultdict(set)
    for r in paired_rows:
        by_issuer[r["normalizedIssuer"]].add((r["ticker"], r["securityId"]))
    ambiguous = {issuer: sorted([list(x) for x in ids]) for issuer, ids in by_issuer.items() if len(ids) > 1}

    ok = [r for r in source_results if "error" not in r]
    paired_counts = sorted(r["pairedRecords"] for r in ok)
    summary = {
        "year": 2006,
        "purpose": "Expanded historical issuer-ticker-security-id master for structural N-Q mapping; no return/performance data used.",
        "sampleRule": f"{SAMPLE_COUNT} deterministic equal-quantile positions across the sorted 2006 primary N-PX filing index; no investment-performance selection.",
        "allNpxFilings": len(filings),
        "primaryNpxFilings": sum(1 for x in filings if x["form"] == "N-PX"),
        "sampleCount": len(samples),
        "fetchSuccess": len(ok),
        "fetchRate": len(ok) / len(samples) if samples else None,
        "uniqueRecords": len(rows),
        "pairedRecords": len(paired_rows),
        "uniqueTickers": len({r["ticker"] for r in paired_rows}),
        "uniqueSecurityIds": len({r["securityId"] for r in paired_rows}),
        "uniqueNormalizedIssuers": len({r["normalizedIssuer"] for r in paired_rows}),
        "ambiguousNormalizedIssuers": len(ambiguous),
        "medianPairedRecordsPerSuccessfulFiling": paired_counts[len(paired_counts)//2] if paired_counts else None,
        "normalizationRule": "Uppercase; &->AND; common legal suffix normalization; punctuation collapsed. Used only for structural issuer matching.",
        "records": rows,
        "ambiguousIssuerMappings": ambiguous,
        "sourceResults": source_results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k not in {"records", "ambiguousIssuerMappings", "sourceResults"}}), flush=True)


if __name__ == "__main__":
    main()
