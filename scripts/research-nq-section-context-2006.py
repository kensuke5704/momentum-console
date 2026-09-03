#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research/nq-section-context-2006.json"
UA = {
    "User-Agent": "momentum-console research kensuke5704@users.noreply.github.com",
    "Accept": "text/plain",
}

# Fixed before inspecting any strategy return. These are the two filings that
# supply all nine frozen PIT-series records in the current 2006 structural sample.
SOURCES = [
    {
        "label": "Select Sector SPDR Trust",
        "filename": "edgar/data/1064641/0000950135-06-001225.txt",
    },
    {
        "label": "streetTRACKS Series Trust",
        "filename": "edgar/data/1064642/0000950135-06-003650.txt",
    },
]

HEADING_PATTERNS = [
    ("COMMON_EQUITY", re.compile(r"\b(?:COMMON\s+STOCKS?|COMMON\s+SHARES?|EQUITIES|EQUITY\s+SECURITIES)\b", re.I)),
    ("PREFERRED", re.compile(r"\bPREFERRED\s+(?:STOCKS?|SHARES?|SECURITIES)\b", re.I)),
    ("DEBT", re.compile(r"\b(?:CORPORATE\s+BONDS?|CORPORATE\s+NOTES?|BONDS?|NOTES?|DEBENTURES?|FIXED\s+INCOME)\b", re.I)),
    ("SHORT_TERM", re.compile(r"\b(?:SHORT[- ]TERM\s+INVESTMENTS?|MONEY\s+MARKET|REPURCHASE\s+AGREEMENTS?)\b", re.I)),
    ("FOREIGN", re.compile(r"\b(?:FOREIGN|NON[- ]U\.?S\.?|INTERNATIONAL)\b", re.I)),
    ("US", re.compile(r"\b(?:UNITED\s+STATES|U\.?S\.?\s+ISSUERS?|DOMESTIC)\b", re.I)),
]


def sec_url(filename: str) -> str:
    return "https://www.sec.gov/Archives/" + filename.lstrip("/")


def fetch_text(filename: str) -> str:
    url = "https://r.jina.ai/" + sec_url(filename)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read(6_000_000).decode("utf-8", "replace")


def plain_lines(text: str) -> list[str]:
    s = re.sub(r"(?is)<BR\s*/?>", "\n", text)
    s = re.sub(r"(?is)</(?:P|DIV|TR|TD|TH|PRE|TABLE|H[1-6])>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return [" ".join(x.split()) for x in s.splitlines() if " ".join(x.split())]


def heading_kind(line: str) -> str | None:
    # Restrict to heading-like lines. This prevents a security issuer such as
    # "United States Steel" from becoming a country heading.
    if len(line) > 120:
        return None
    upper = line.upper()
    if re.search(r"\$|\d{3,}", line):
        return None
    if not any(k in upper for k in ("STOCK", "SHARE", "EQU", "BOND", "NOTE", "DEBT", "SHORT", "MONEY", "FOREIGN", "INTERNATIONAL", "UNITED STATES", "DOMESTIC", "INVESTMENT")):
        return None
    for kind, pat in HEADING_PATTERNS:
        if pat.search(line):
            return kind
    return None


def main() -> None:
    results = []
    total_counts: dict[str, int] = {}
    for source in SOURCES:
        text = fetch_text(source["filename"])
        lines = plain_lines(text)
        hits = []
        counts: dict[str, int] = {}
        for i, line in enumerate(lines):
            kind = heading_kind(line)
            if not kind:
                continue
            counts[kind] = counts.get(kind, 0) + 1
            total_counts[kind] = total_counts.get(kind, 0) + 1
            hits.append({
                "kind": kind,
                "line": line,
                "lineIndex": i,
                "following": lines[i + 1:i + 5],
            })
        results.append({
            **source,
            "lineCount": len(lines),
            "headingCounts": counts,
            "headingHits": hits,
        })
        print(source["label"], json.dumps(counts), flush=True)
        for h in hits[:25]:
            print(" ", h["kind"], "::", h["line"][:140], flush=True)

    out = {
        "year": 2006,
        "purpose": "Structural diagnostic for whether legacy N-Q schedule headings can supply asset-class/country context analogous to N-PORT EC/US fields. No strategy-return data used.",
        "sourceRule": "The two fixed filings underlying the frozen nine-series 2006 PIT sample; source choice is not based on mapping misses or returns.",
        "classificationStatus": "Diagnostic only. Heading detection does not yet filter holdings or alter the historical universe.",
        "totalHeadingCounts": total_counts,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
