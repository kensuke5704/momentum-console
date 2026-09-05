#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "data/research/sec-legacy-etf-series-source-q4-2005.json"
OUT = ROOT / "data/research/sec-legacy-series-operational-locality-diagnostic-2005.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

base = load_module("catalog_base", ROOT / "scripts/research-sec-historical-etf-series-source-catalog-h1-2006.py")

CREATION = re.compile(r"\bCREATION\s+UNITS?\b", re.I)
EXCHANGE = re.compile(r"\b(?:LISTED|LISTING|TRADED|TRADING)\b.{0,120}\b(?:EXCHANGE|NYSE|AMEX|NASDAQ)\b|\b(?:EXCHANGE|NYSE|AMEX|NASDAQ)\b.{0,120}\b(?:LISTED|LISTING|TRADED|TRADING)\b", re.I)
ETF_CLASS = re.compile(r"\b(?:VIPER(?:\s+SHARES?)?|ETF\s+SHARES?|EXCHANGE\s+TRADED\s+SHARES?)\b", re.I)


def positions(pattern: re.Pattern, text: str) -> list[int]:
    return [m.start() for m in pattern.finditer(text)]


def nearest(a: list[int], b: list[int]) -> int | None:
    if not a or not b:
        return None
    return min(abs(x-y) for x in a for y in b)


def main() -> None:
    legacy = json.loads(LEGACY.read_text())
    by_file = defaultdict(list)
    for row in legacy["legacySeries"]:
        by_file[row["evidenceFilename"]].append(row)
    diagnostics = []
    filing_errors = []
    for filename, rows in sorted(by_file.items()):
        try:
            raw, transport, _, prior = base.ft(base.su(filename), 4_000_000, 22)
            text = base.norm(raw)
            creation_pos = positions(CREATION, text)
            exchange_pos = positions(EXCHANGE, text)
            class_pos = positions(ETF_CLASS, text)
            for row in rows:
                title = row["normalizedSeriesName"]
                title_pos = [m.start() for m in re.finditer(re.escape(title), text)]
                diagnostics.append({
                    "legacyIdentity": row["legacyIdentity"],
                    "cik": row["cik"],
                    "seriesName": row["seriesName"],
                    "normalizedSeriesName": title,
                    "evidenceDateFiled": row["evidenceDateFiled"],
                    "evidenceForm": row["evidenceForm"],
                    "evidenceFilename": filename,
                    "titleOccurrenceCount": len(title_pos),
                    "creationOccurrenceCount": len(creation_pos),
                    "exchangeOccurrenceCount": len(exchange_pos),
                    "explicitEtfClassOccurrenceCount": len(class_pos),
                    "nearestCreationChars": nearest(title_pos, creation_pos),
                    "nearestExchangeChars": nearest(title_pos, exchange_pos),
                    "nearestExplicitEtfClassChars": nearest(title_pos, class_pos),
                    "within2kCreationAndExchange": bool(title_pos and nearest(title_pos, creation_pos) is not None and nearest(title_pos, creation_pos) <= 2000 and nearest(title_pos, exchange_pos) is not None and nearest(title_pos, exchange_pos) <= 2000),
                    "within5kCreationAndExchange": bool(title_pos and nearest(title_pos, creation_pos) is not None and nearest(title_pos, creation_pos) <= 5000 and nearest(title_pos, exchange_pos) is not None and nearest(title_pos, exchange_pos) <= 5000),
                    "within10kCreationAndExchange": bool(title_pos and nearest(title_pos, creation_pos) is not None and nearest(title_pos, creation_pos) <= 10000 and nearest(title_pos, exchange_pos) is not None and nearest(title_pos, exchange_pos) <= 10000),
                    "within5kExplicitEtfClass": bool(title_pos and nearest(title_pos, class_pos) is not None and nearest(title_pos, class_pos) <= 5000),
                    "transport": transport,
                    "priorErrors": prior,
                })
        except Exception as exc:
            filing_errors.append({"filename": filename, "error": type(exc).__name__, "errorDetail": str(exc)[:700]})

    out = {
        "purpose": (
            "Outcome-independent document-locality diagnostic for pre-Series-ID legacy source titles. For each "
            "title already matched to a strict issuer-own operational filing, measure character distance to the "
            "nearest Creation Unit phrase, exchange listing/trading phrase, and explicit VIPER/ETF Shares phrase. "
            "This diagnostic is used to reject broad mixed-trust context matches; it does not use holdings, later "
            "Series IDs, returns, ranks, or strategy outcomes."
        ),
        "source": "LEGACY_SERIES_OPERATIONAL_LOCALITY_DIAGNOSTIC_V1",
        "seriesCount": len(diagnostics),
        "filingCount": len(by_file),
        "filingErrorCount": len(filing_errors),
        "within2kCreationAndExchangeCount": sum(x["within2kCreationAndExchange"] for x in diagnostics),
        "within5kCreationAndExchangeCount": sum(x["within5kCreationAndExchange"] for x in diagnostics),
        "within10kCreationAndExchangeCount": sum(x["within10kCreationAndExchange"] for x in diagnostics),
        "within5kExplicitEtfClassCount": sum(x["within5kExplicitEtfClass"] for x in diagnostics),
        "diagnostics": diagnostics,
        "filingErrors": filing_errors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k:v for k,v in out.items() if k not in ("diagnostics","filingErrors")}), flush=True)
    for row in diagnostics:
        print("SERIES", json.dumps({k:row[k] for k in (
            "cik","seriesName","nearestCreationChars","nearestExchangeChars","nearestExplicitEtfClassChars",
            "within2kCreationAndExchange","within5kCreationAndExchange","within10kCreationAndExchange","within5kExplicitEtfClass"
        )}), flush=True)

if __name__ == "__main__":
    main()
