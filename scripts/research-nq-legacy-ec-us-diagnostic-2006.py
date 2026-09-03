#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research/nq-legacy-ec-us-diagnostic-2006.json"

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts" / "research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)

SOURCES = [
    {"company": "SELECT SECTOR SPDR TRUST", "cik": "1064641", "filename": "edgar/data/1064641/0000950135-06-001225.txt"},
    {"company": "RYDEX ETF TRUST", "cik": "1208211", "filename": "edgar/data/1208211/0000950135-06-001815.txt"},
    {"company": "STREETTRACKS SERIES TRUST", "cik": "1064642", "filename": "edgar/data/1064642/0000950135-06-003650.txt"},
]

COMMON = re.compile(r"\bCOMMON\s+(?:STOCKS?|SHARES?)\s*--\s*([0-9]+(?:\.[0-9]+)?)\s*%", re.I)
PREFERRED = re.compile(r"\bPREFERRED\s+(?:STOCKS?|SHARES?|SECURITIES)\s*--\s*([0-9]+(?:\.[0-9]+)?)\s*%", re.I)
SHORT_TERM = re.compile(r"\bSHORT[- ]TERM\s+INVESTMENTS?\s*--\s*([0-9]+(?:\.[0-9]+)?)\s*%", re.I)
ADR = re.compile(r"\b(?:ADR|GDR|DEPOSITARY\s+RECEIPT)\b", re.I)

# Fixed structural dictionary, not inferred from target holdings or returns.
COUNTRIES = {
    "ARGENTINA", "AUSTRALIA", "AUSTRIA", "BELGIUM", "BRAZIL", "CANADA", "CHILE", "CHINA",
    "DENMARK", "FINLAND", "FRANCE", "GERMANY", "HONG KONG", "INDIA", "IRELAND", "ISRAEL", "ITALY",
    "JAPAN", "MEXICO", "NETHERLANDS", "NORWAY", "PORTUGAL", "SINGAPORE", "SOUTH AFRICA", "SOUTH KOREA",
    "SPAIN", "SWEDEN", "SWITZERLAND", "TAIWAN", "UNITED KINGDOM", "UNITED STATES",
}
COUNTRY_LINE = re.compile(r"\b([A-Z][A-Z .&'-]{2,40})\s*--\s*([0-9]+(?:\.[0-9]+)?)\s*%")


def first_pct(pattern: re.Pattern, text: str) -> float | None:
    m = pattern.search(text)
    return float(m.group(1)) if m else None


def country_allocations(vis: str) -> list[dict]:
    found = []
    for m in COUNTRY_LINE.finditer(vis.upper()):
        name = " ".join(m.group(1).split()).strip(" .-")
        if name in COUNTRIES:
            found.append({"country": name, "weightPct": float(m.group(2))})
    # preserve first appearance per country; repeated continuation headers are not allocations
    out, seen = [], set()
    for row in found:
        if row["country"] not in seen:
            seen.add(row["country"])
            out.append(row)
    return out


def main() -> None:
    rows = []
    for source in SOURCES:
        try:
            _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(source["filename"]))
            series = seg.meta.parse_series_contracts(submission, source["company"])
            etf = [s for s in series if s["isEtf"]]
            by_id = {s.get("seriesId"): s for s in etf if s.get("seriesId")}
            _, text = seg.embedded_primary_nq(submission)
            grouped, _ = seg.grouped_schedule_blocks(text, etf)
            for sid, blocks in grouped.items():
                s = by_id.get(sid)
                if not s or not seg.eligible_name(s.get("seriesName") or ""):
                    continue
                combined = "\n".join(blocks)
                vis = seg.visible(combined)
                countries = country_allocations(vis)
                row = {
                    "seriesId": sid,
                    "seriesName": s.get("seriesName"),
                    "fundTickers": s.get("etfTickers", []),
                    "schedulePages": len(blocks),
                    "commonStockPct": first_pct(COMMON, vis),
                    "preferredPct": first_pct(PREFERRED, vis),
                    "shortTermPct": first_pct(SHORT_TERM, vis),
                    "explicitCountryAllocations": countries,
                    "explicitCountryCount": len(countries),
                    "explicitUnitedStatesPct": next((r["weightPct"] for r in countries if r["country"] == "UNITED STATES"), None),
                    "adrOrGdrMentions": len(ADR.findall(vis)),
                }
                rows.append(row)
                print("SERIES", json.dumps(row), flush=True)
        except Exception as e:
            print("FAIL", source["company"], repr(e), flush=True)

    common_known = [r for r in rows if r["commonStockPct"] is not None]
    country_known = [r for r in rows if r["explicitCountryCount"] > 0]
    adr_rows = [r for r in rows if r["adrOrGdrMentions"] > 0]
    out = {
        "year": 2006,
        "purpose": "Structural diagnostic for legacy analogues of N-PORT ASSET_CAT=EC and INVESTMENT_COUNTRY=US on corrected explicit-series N-Q schedules. No returns/performance data used.",
        "ecInterpretation": "An explicit COMMON STOCK(S/SHARES) allocation is direct schedule-level evidence for equity-class content. It is diagnostic only and does not yet replace per-holding ASSET_CAT=EC.",
        "usInterpretation": "Explicit country allocations are accepted only when the filing prints a recognized country heading. Absence of country headings is UNKNOWN, not automatically US. ADR/GDR mentions are flags only, not country assignments.",
        "seriesExamined": len(rows),
        "seriesWithExplicitCommonStockPct": len(common_known),
        "seriesWithExplicitCountryAllocations": len(country_known),
        "seriesWithAdrOrGdrMentions": len(adr_rows),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
