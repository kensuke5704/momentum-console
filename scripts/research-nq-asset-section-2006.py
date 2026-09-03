#!/usr/bin/env python3
from __future__ import annotations

import html
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "data/research/nq-index-2006.json"
OUT = ROOT / "data/research/nq-asset-section-2006.json"

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts/research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)

TARGET = re.compile(r"SELECT SECTOR SPDR|STREETTRACKS|POWERSHARES EXCHANGE TRADED|RYDEX ETF TRUST|PROSHARES", re.I)
TAIL_RE = re.compile(r"^(.*?)(\d[\d,]*(?:\.\d+)?)\s+(?:([A-Z]{3})\s+)?\$?\s*(\d[\d,]*(?:\.\d+)?)\s*$")

SECTION_RULES = [
    ("COMMON_EQUITY", re.compile(r"^\s*(?:TOTAL\s+)?COMMON\s+(?:STOCKS?|SHARES?)\b", re.I)),
    ("PREFERRED", re.compile(r"^\s*(?:TOTAL\s+)?PREFERRED\s+(?:STOCKS?|SHARES?|SECURITIES)\b", re.I)),
    ("SHORT_TERM", re.compile(r"^\s*(?:TOTAL\s+)?SHORT[- ]TERM\s+INVESTMENTS?\b|^\s*MONEY\s+MARKET\s+FUND\b", re.I)),
    ("DEBT", re.compile(r"^\s*(?:TOTAL\s+)?(?:CORPORATE\s+)?(?:BONDS?|NOTES?|DEBENTURES?|FIXED\s+INCOME)\b", re.I)),
]


def plain_lines(text: str) -> list[str]:
    s = re.sub(r"(?is)<BR\s*/?>", "\n", text)
    s = re.sub(r"(?is)</(?:P|DIV|TR|TD|PRE|TABLE)>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return [" ".join(x.split()) for x in s.splitlines()]


def parse_number(s: str):
    s = s.strip().replace("$", "").replace(",", "").replace(" ", "")
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", s):
        return None
    try:
        v = float(s)
    except Exception:
        return None
    return -v if neg else v


def clean_desc(s: str) -> str:
    s = re.sub(r"^[\s*]+", "", s)
    s = re.sub(r"^(?:\([a-z0-9,]+\))+", "", s, flags=re.I)
    s = re.sub(r"\.{2,}\s*$", "", s)
    return " ".join(s.split())


def section_from_line(line: str) -> str | None:
    # Section transitions must be explicit left-edge schedule headings. Company
    # names containing words such as International are never used as headings.
    for section, pat in SECTION_RULES:
        if pat.search(line):
            return section
    return None


def parse_plain_with_sections(text: str) -> list[dict]:
    lines = plain_lines(text)
    holdings: list[dict] = []
    pending = ""
    started = False
    ended = False
    section = "UNKNOWN"
    for line in lines:
        if not line:
            continue
        up = line.upper()
        if any(k in up for k in ("STATEMENT OF INVESTMENTS", "SCHEDULE OF INVESTMENTS")):
            started = True
            continue
        if not started:
            continue
        if any(k in up for k in ("ITEM 2. CONTROLS", "ITEM 2. OTHER INFORMATION", "NOTES TO STATEMENT OF INVESTMENTS")):
            if len(holdings) >= 5:
                ended = True
        if ended:
            break

        new_section = section_from_line(line)
        if new_section:
            section = new_section
            pending = ""
            continue
        if re.fullmatch(r"[-_= .]+", line) or re.fullmatch(r"[\d,()$ .]+", line):
            continue

        m = TAIL_RE.match(line)
        if m:
            prefix, qty, currency, value = m.groups()
            desc = clean_desc(prefix)
            q = parse_number(qty)
            v = parse_number(value)
            if v is None or v <= 0 or q is None or q <= 0:
                continue
            if not re.search(r"[A-Za-z]{2}", desc):
                continue
            child = bool(re.match(r"^(?:\(?[a-z](?:,[a-z])*\)?\s*)?(?:REG\s+S|FRN|SERIES|SECURED|ZERO|\d+(?:\.\d+)?%)", desc, re.I))
            full = " ".join(x for x in ((pending if child else ""), desc) if x).strip()
            if len(full) < 6:
                continue
            holdings.append({
                "description": full,
                "quantityOrPrincipal": q,
                "marketValue": v,
                "currency": currency,
                "assetSection": section,
            })
            continue

        if "%" not in line and 5 <= len(line) <= 220 and re.search(r"[A-Za-z]{3}", line) and line.rstrip().endswith(","):
            pending = clean_desc(line)
        elif re.search(r"\b(?:LONG TERM INVESTMENTS|TOTAL)\b", up):
            pending = ""

    # Keep the same dedupe key as the production-independent parser pilot.
    out = []
    seen = set()
    for h in holdings:
        key = (h["description"], h.get("quantityOrPrincipal"), h["marketValue"])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def main() -> None:
    idx = json.loads(IDX.read_text())
    filings = [x for x in idx["filings"] if x.get("form") == "N-Q" and TARGET.search(str(x.get("company") or ""))]
    chosen = []
    seen = set()
    for x in filings:
        if x["cik"] in seen:
            continue
        seen.add(x["cik"])
        chosen.append(x)

    series_rows = []
    for x in chosen:
        try:
            _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(x["filename"]))
            series = seg.meta.parse_series_contracts(submission, x["company"])
            etf = [s for s in series if s["isEtf"]]
            _, text = seg.embedded_primary_nq(submission)
            markers = list(seg.SCHEDULE.finditer(text))
            mapped = {}
            for j, marker in enumerate(markers):
                start = marker.start()
                end = markers[j + 1].start() if j + 1 < len(markers) else min(len(text), start + 300000)
                block = text[start:end]
                s, score = seg.map_schedule_to_series(block, etf)
                if not s or not s.get("seriesId"):
                    continue
                holdings = parse_plain_with_sections(block)
                positive = [h for h in holdings if h["marketValue"] > 0]
                total = sum(h["marketValue"] for h in positive)
                if total > 0:
                    for h in positive:
                        h["weight"] = 100.0 * h["marketValue"] / total
                    positive.sort(key=lambda h: h["weight"], reverse=True)
                top10 = sum(h.get("weight", 0) for h in positive[:10])
                usable = bool(seg.eligible_name(s.get("seriesName") or "") and 10 <= len(positive) <= 120 and total > 0 and top10 >= 25.0)
                candidate = (len(positive), score, positive, usable)
                current = mapped.get(s["seriesId"])
                if current is None or candidate[:2] > current[:2]:
                    mapped[s["seriesId"]] = candidate

            for s in etf:
                if s.get("seriesId") not in mapped:
                    continue
                count, score, holdings, usable = mapped[s["seriesId"]]
                if not usable:
                    continue
                section_count: dict[str, int] = {}
                section_weight: dict[str, float] = {}
                for h in holdings:
                    sec = h["assetSection"]
                    section_count[sec] = section_count.get(sec, 0) + 1
                    section_weight[sec] = section_weight.get(sec, 0.0) + h.get("weight", 0.0)
                attributed_count = sum(v for k, v in section_count.items() if k != "UNKNOWN")
                attributed_weight = sum(v for k, v in section_weight.items() if k != "UNKNOWN")
                row = {
                    "seriesId": s.get("seriesId"),
                    "seriesName": s.get("seriesName"),
                    "fundTickers": s.get("etfTickers", []),
                    "mappingScore": score,
                    "holdingCount": count,
                    "sectionCount": section_count,
                    "sectionWeight": section_weight,
                    "attributedCountRate": attributed_count / count if count else None,
                    "attributedWeightRate": attributed_weight / 100.0 if holdings else None,
                    "commonEquityCount": section_count.get("COMMON_EQUITY", 0),
                    "commonEquityWeight": section_weight.get("COMMON_EQUITY", 0.0),
                    "unknownExamples": [h["description"] for h in holdings if h["assetSection"] == "UNKNOWN"][:10],
                }
                series_rows.append(row)
                print("SERIES", json.dumps(row), flush=True)
        except Exception as e:
            print("FAIL", x.get("company"), repr(e), flush=True)

    total_count = sum(r["holdingCount"] for r in series_rows)
    common_count = sum(r["commonEquityCount"] for r in series_rows)
    # Series weights each normalize to 100, so this aggregate is diagnostic only.
    common_weight = sum(r["commonEquityWeight"] for r in series_rows)
    out = {
        "year": 2006,
        "purpose": "Structural pilot attributing parsed N-Q holdings to explicit schedule asset-class sections, as a candidate legacy analogue for N-PORT ASSET_CAT=EC. No return/performance data used.",
        "rule": "Carry forward only explicit left-edge schedule headings: COMMON STOCK(S/SHARES), PREFERRED, SHORT-TERM/MONEY MARKET, or DEBT. Unknown remains unknown; no issuer-name inference.",
        "status": "Diagnostic only; does not yet filter historical universe inputs.",
        "seriesCount": len(series_rows),
        "holdingCount": total_count,
        "commonEquityCount": common_count,
        "commonEquityCountRate": common_count / total_count if total_count else None,
        "meanCommonEquityWeightAcrossSeries": common_weight / len(series_rows) if series_rows else None,
        "series": series_rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "series"}), flush=True)


if __name__ == "__main__":
    main()
