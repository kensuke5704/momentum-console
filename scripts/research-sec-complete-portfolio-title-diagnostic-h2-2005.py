#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/research/sec-complete-portfolio-inventory-h2-2005.json"
PREF = ROOT / "data/research/sec-etf-registrant-operational-prefilter-h1-2006.json"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "text/plain,text/html,*/*",
    "Accept-Encoding": "identity",
}
SCHEDULE = re.compile(
    r"SCHEDULE OF PORTFOLIO INVESTMENTS|SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|"
    r"PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS|STATEMENT OF NET ASSETS|SCHEDULE OF SECURITIES",
    re.I,
)
DOCUMENT_BLOCK = re.compile(r"(?is)<DOCUMENT>(.*?)</DOCUMENT>")
TYPE = re.compile(r"(?im)^\s*<TYPE>\s*([^\s<]+)")
FILENAME = re.compile(r"(?im)^\s*<FILENAME>\s*([^\s<]+)")
DESCRIPTION = re.compile(r"(?im)^\s*<DESCRIPTION>\s*(.*?)\s*$")
TEXT_BLOCK = re.compile(r"(?is)<TEXT>(.*)</TEXT>")


def fetch(filename: str) -> tuple[str, str]:
    url = "https://www.sec.gov/Archives/" + filename.lstrip("/")
    errors = []
    for target in (url, "https://r.jina.ai/" + url):
        try:
            req = urllib.request.Request(target, headers=UA)
            with urllib.request.urlopen(req, timeout=35) as r:
                data = r.read(25_000_000)
            return data.decode("latin-1", "replace"), target
        except Exception as exc:
            errors.append(f"{type(exc).__name__}:{target}")
    raise RuntimeError(";".join(errors))


def primary_document(submission: str, filing_form: str) -> tuple[str, str, str, str]:
    wanted = filing_form.upper().replace("/A", "")
    candidates = []
    for dm in DOCUMENT_BLOCK.finditer(submission):
        block = dm.group(1)
        tm = TYPE.search(block)
        doc_type = tm.group(1).strip().upper() if tm else ""
        filename_m = FILENAME.search(block)
        desc_m = DESCRIPTION.search(block)
        text_m = TEXT_BLOCK.search(block)
        item = (
            filename_m.group(1).strip() if filename_m else "embedded-document",
            desc_m.group(1).strip() if desc_m else "",
            text_m.group(1) if text_m else block,
            doc_type,
        )
        if doc_type == filing_form.upper():
            return item
        if doc_type.replace("/A", "") == wanted:
            candidates.append(item)
    if candidates:
        return candidates[0]
    return "submission", "", submission, ""


def line_text(raw: str) -> str:
    s = re.sub(r"(?is)<(?:br|p|div|tr|td|th|li|h[1-6])\b[^>]*>", "\n", raw)
    s = re.sub(r"(?is)</(?:p|div|tr|td|th|li|h[1-6])>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return "\n".join(" ".join(x.split()) for x in s.splitlines() if " ".join(x.split()))


def marker_windows(raw: str) -> list[dict]:
    text = line_text(raw)
    out = []
    for i, match in enumerate(SCHEDULE.finditer(text)):
        before = text[max(0, match.start() - 1800):match.start()].splitlines()[-18:]
        after = text[match.end():min(len(text), match.end() + 1800)].splitlines()[:18]
        out.append({
            "markerIndex": i,
            "marker": match.group(0),
            "beforeLines": before,
            "afterLines": after,
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--shards", type=int, default=4)
    args = ap.parse_args()

    inv = json.loads(INV.read_text())
    pref = json.loads(PREF.read_text())
    candidate_ciks = set(pref["positiveCiks"])
    rows = [r for r in inv["rows"] if r["cik"] in candidate_ciks]
    rows.sort(key=lambda r: (r["dateFiled"], r["form"], r["cik"], r["filename"]))
    selected = [r for i, r in enumerate(rows) if i % args.shards == args.shard]

    results = []
    for i, row in enumerate(selected, 1):
        rec = {k: row.get(k) for k in ("cik", "company", "form", "dateFiled", "accession", "filename")}
        try:
            submission, transport = fetch(row["filename"])
            primary, description, text, doc_type = primary_document(submission, row["form"])
            windows = marker_windows(text)
            rec.update({
                "transport": transport,
                "primaryDocument": primary,
                "primaryDocumentType": doc_type,
                "documentDescription": description,
                "scheduleMarkerCount": len(windows),
                "hasCompletePortfolioSchedule": bool(windows),
                "scheduleWindows": windows,
            })
        except Exception as exc:
            rec["error"] = type(exc).__name__
            rec["errorDetail"] = str(exc)[:900]
        results.append(rec)
        print("FILING", json.dumps({
            "i": i, "n": len(selected), "cik": row["cik"], "form": row["form"],
            "dateFiled": row["dateFiled"], "markers": rec.get("scheduleMarkerCount"), "error": rec.get("error")
        }), flush=True)

    out = {
        "purpose": (
            "Production-independent structural diagnostic of H2 2005 complete-portfolio filings for candidate "
            "registrants from the existing operational prefilter. N-Q/N-Q-A and certified annual/semiannual "
            "shareholder reports N-CSR/N-CSRS plus amendments are inspected. Accepted complete-portfolio headings "
            "include the observed historical 'Statement of Net Assets' grammar. An amendment is a holdings source "
            "only when its own primary filing document contains an accepted complete-portfolio schedule. Only "
            "explicit schedule headings and nearby filing text are retained. No holdings outcomes, later Series "
            "IDs, ranks, returns, or strategy results are used."
        ),
        "shard": args.shard,
        "shards": args.shards,
        "candidateRegistrantCount": len(candidate_ciks),
        "candidateFilingCount": len(rows),
        "selectedFilingCount": len(selected),
        "fetchSuccessCount": sum("error" not in x for x in results),
        "fetchErrorCount": sum("error" in x for x in results),
        "scheduleMarkerCount": sum(x.get("scheduleMarkerCount", 0) for x in results),
        "completePortfolioSourceCount": sum(bool(x.get("hasCompletePortfolioSchedule")) for x in results),
        "amendmentCount": sum(str(x.get("form", "")).endswith("/A") for x in results),
        "amendmentCompletePortfolioSourceCount": sum(str(x.get("form", "")).endswith("/A") and bool(x.get("hasCompletePortfolioSchedule")) for x in results),
        "results": results,
    }
    out_path = ROOT / "data" / "research" / f"sec-complete-portfolio-title-diagnostic-h2-2005-shard-{args.shard}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
