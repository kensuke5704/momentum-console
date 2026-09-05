#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/research/sec-marketwide-nq-lookback-q4-2005.json"
PREF = ROOT / "data/research/sec-etf-registrant-operational-prefilter-h1-2006.json"
OUT = ROOT / "data/research/nq-legacy-series-title-diagnostic-q4-2005.json"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "text/plain,text/html,*/*",
    "Accept-Encoding": "identity",
}
SCHEDULE = re.compile(
    r"SCHEDULE OF PORTFOLIO INVESTMENTS|SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS",
    re.I,
)
DOCUMENT_BLOCK = re.compile(r"(?is)<DOCUMENT>(.*?)</DOCUMENT>")
TYPE_NQ = re.compile(r"(?im)^\s*<TYPE>\s*N-Q\b")
FILENAME = re.compile(r"(?im)^\s*<FILENAME>\s*([^\s<]+)")
DESCRIPTION = re.compile(r"(?im)^\s*<DESCRIPTION>\s*(.*?)\s*$")
TEXT_BLOCK = re.compile(r"(?is)<TEXT>(.*)</TEXT>")


def fetch(filename: str) -> tuple[str, str]:
    url = "https://www.sec.gov/Archives/" + filename.lstrip("/")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as response:
        payload = response.read(25_000_000)
    return payload.decode("latin-1", "replace"), url


def primary_nq(submission: str) -> tuple[str, str, str]:
    for dm in DOCUMENT_BLOCK.finditer(submission):
        block = dm.group(1)
        if not TYPE_NQ.search(block):
            continue
        filename_m = FILENAME.search(block)
        desc_m = DESCRIPTION.search(block)
        text_m = TEXT_BLOCK.search(block)
        return (
            filename_m.group(1).strip() if filename_m else "embedded-nq",
            desc_m.group(1).strip() if desc_m else "",
            text_m.group(1) if text_m else block,
        )
    return "submission", "", submission


def line_text(raw: str) -> str:
    s = re.sub(r"(?is)<(?:br|p|div|tr|td|th|li|h[1-6])\b[^>]*>", "\n", raw)
    s = re.sub(r"(?is)</(?:p|div|tr|td|th|li|h[1-6])>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    lines = []
    for line in s.splitlines():
        line = " ".join(line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)


def marker_windows(raw: str) -> list[dict]:
    text = line_text(raw)
    out = []
    for i, m in enumerate(SCHEDULE.finditer(text)):
        start = max(0, m.start() - 1600)
        end = min(len(text), m.end() + 1600)
        before = text[start:m.start()].splitlines()[-16:]
        after = text[m.end():end].splitlines()[:16]
        out.append({
            "markerIndex": i,
            "marker": m.group(0),
            "beforeLines": before,
            "afterLines": after,
        })
    return out


def main() -> None:
    inv = json.loads(INV.read_text())
    pref = json.loads(PREF.read_text())
    candidate = set(pref["positiveCiks"])
    rows = [row for row in inv["rows"] if row["cik"] in candidate]
    results = []
    for i, row in enumerate(rows, 1):
        rec = {k: row[k] for k in ("cik", "company", "dateFiled", "accession", "filename")}
        try:
            submission, url = fetch(row["filename"])
            primary, description, text = primary_nq(submission)
            windows = marker_windows(text)
            rec.update({
                "transport": url,
                "primaryDocument": primary,
                "documentDescription": description,
                "scheduleMarkerCount": len(windows),
                "scheduleWindows": windows,
            })
        except Exception as exc:
            rec["error"] = type(exc).__name__
            rec["errorDetail"] = str(exc)[:900]
        results.append(rec)
        print("FILING", json.dumps({
            "index": i,
            "total": len(rows),
            "cik": row["cik"],
            "company": row["company"],
            "dateFiled": row["dateFiled"],
            "markers": rec.get("scheduleMarkerCount"),
            "error": rec.get("error"),
        }), flush=True)

    out = {
        "purpose": (
            "Diagnose explicit legacy Series/Fund titles printed around Q4 2005 N-Q schedule headings before "
            "mandatory SEC Series/Class identifiers took effect on 2006-02-06. The population is all Q4 N-Q/N-Q-A "
            "filings belonging to the independently generated H1 operational-prefilter candidate CIKs. Context "
            "windows are evidence only; no holdings outcomes, later Series IDs, ranks, returns, or strategy results "
            "are used to construct titles."
        ),
        "source": "Q4_2005_NQ_EXPLICIT_SCHEDULE_TITLE_DIAGNOSTIC_V1",
        "candidateRegistrantCount": len(candidate),
        "q4CandidateFilingCount": len(rows),
        "fetchSuccessCount": sum("error" not in row for row in results),
        "fetchErrorCount": sum("error" in row for row in results),
        "scheduleMarkerCount": sum(row.get("scheduleMarkerCount", 0) for row in results),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
