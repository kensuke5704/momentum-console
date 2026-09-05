#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load("hybrid_raw", ROOT / "scripts/research-nq-pit-holdings-hybrid-h1-2006.py")
COUNTRIES = {
    "ARGENTINA", "AUSTRALIA", "AUSTRIA", "BELGIUM", "BRAZIL", "CANADA", "CHILE", "CHINA",
    "DENMARK", "FINLAND", "FRANCE", "GERMANY", "HONG KONG", "INDIA", "IRELAND", "ISRAEL", "ITALY",
    "JAPAN", "MEXICO", "NETHERLANDS", "NORWAY", "PORTUGAL", "SINGAPORE", "SOUTH AFRICA", "SOUTH KOREA",
    "SPAIN", "SWEDEN", "SWITZERLAND", "TAIWAN", "UNITED KINGDOM", "UNITED STATES",
}
COUNTRY_LINE = re.compile(r"\b([A-Z][A-Z .&'-]{2,40})\s*(?:--|[-–—])\s*([0-9]+(?:\.[0-9]+)?)\s*%", re.I)
RESET = re.compile(r"\b(?:SHORT[- ]TERM INVESTMENTS?|MONEY MARKET|NET ASSETS)\b", re.I)


def qnorm(value):
    value = re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", value or "", flags=re.I)
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", value.upper()).split())


def country_stream(combined):
    visible = base.seg.visible(combined)
    state = "UNKNOWN"
    rows = []
    for raw in visible.splitlines():
        line = " ".join(raw.split()).strip()
        if not line:
            continue
        match = COUNTRY_LINE.search(line.upper())
        if match:
            name = " ".join(match.group(1).split()).strip(" .-")
            if name in COUNTRIES:
                state = "US" if name == "UNITED STATES" else "NON_US"
                continue
        if RESET.search(line):
            state = "UNKNOWN"
        rows.append((qnorm(line), state))
    return rows


def locate_country(description, rows):
    query = qnorm(description)
    if not query:
        return "UNKNOWN"
    hits = [state for text, state in rows if state != "UNKNOWN" and query in text]
    if not hits:
        tokens = query.split()
        anchor = " ".join(tokens[:min(4, len(tokens))])
        if len(anchor) >= 6:
            hits = [state for text, state in rows if state != "UNKNOWN" and anchor in text]
    return hits[0] if hits and all(value == hits[0] for value in hits) else "UNKNOWN"


_original_annotate_sections = base.annotate_sections


def annotate_sections(holdings, combined):
    annotated, counts, weights = _original_annotate_sections(holdings, combined)
    stream = country_stream(combined)
    output = []
    for holding in annotated:
        country = locate_country(holding.get("description") or "", stream)
        row = dict(holding)
        row["legacyCountryClassification"] = country
        if country != "UNKNOWN":
            row["legacyCountryMethod"] = "NQ_EXPLICIT_COUNTRY_SECTION"
        output.append(row)
    return output, counts, weights


base.annotate_sections = annotate_sections

if __name__ == "__main__":
    base.main()
