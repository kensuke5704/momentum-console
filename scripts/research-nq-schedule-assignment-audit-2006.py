#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research/nq-schedule-assignment-audit-2006.json"
SOURCE = {
    "company": "STREETTRACKS SERIES TRUST",
    "cik": "1064642",
    "filename": "edgar/data/1064642/0000950135-06-003650.txt",
}

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts/research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)


def clean_excerpt(block: str, limit: int = 35) -> list[str]:
    text = re.sub(r"(?is)<BR\s*/?>", "\n", block)
    text = re.sub(r"(?is)</(?:P|DIV|TR|TD|TH|PRE|TABLE|H[1-6])>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    lines = [" ".join(x.split()) for x in text.splitlines()]
    lines = [x for x in lines if x]
    return lines[:limit]


def main() -> None:
    _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(SOURCE["filename"]))
    series = seg.meta.parse_series_contracts(submission, SOURCE["company"])
    etf = [s for s in series if s["isEtf"]]
    primary, text = seg.embedded_primary_nq(submission)
    markers = list(seg.SCHEDULE.finditer(text))

    rows = []
    for j, marker in enumerate(markers):
        start = marker.start()
        end = markers[j + 1].start() if j + 1 < len(markers) else min(len(text), start + 300000)
        block = text[start:end]
        mapped, score = seg.map_schedule_to_series(block, etf)
        method, _, _, holdings = seg.nqpilot.parse_holdings(block)
        row = {
            "scheduleIndex": j,
            "marker": marker.group(0),
            "mappedSeriesId": mapped.get("seriesId") if mapped else None,
            "mappedSeriesName": mapped.get("seriesName") if mapped else None,
            "mappedTickers": mapped.get("etfTickers", []) if mapped else [],
            "mappingScore": score,
            "parseMethod": method,
            "parsedHoldingCount": len(holdings),
            "sampleHoldings": [h.get("description") for h in holdings[:12]],
            "excerpt": clean_excerpt(block),
        }
        rows.append(row)
        print("SCHEDULE", json.dumps({k: row[k] for k in ("scheduleIndex", "mappedSeriesName", "mappedTickers", "mappingScore", "parsedHoldingCount", "sampleHoldings")}), flush=True)
        for line in row["excerpt"][:12]:
            print("  ", line[:180], flush=True)

    out = {
        "year": 2006,
        "purpose": "Audit schedule-block to ETF-series assignment in the fixed streetTRACKS N-Q source after implausible holdings were observed in assigned series. Structural evidence only; no returns used.",
        "source": SOURCE,
        "primaryDocument": primary,
        "registeredEtfSeries": [{"seriesId": s.get("seriesId"), "seriesName": s.get("seriesName"), "tickers": s.get("etfTickers", [])} for s in etf],
        "scheduleCount": len(markers),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({"registeredEtfSeries": len(etf), "scheduleCount": len(markers)}), flush=True)


if __name__ == "__main__":
    main()
