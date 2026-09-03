#!/usr/bin/env python3
from __future__ import annotations

import html
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "data" / "research" / "nq-index-2006.json"
OUT = ROOT / "data" / "research" / "nq-series-segmentation-2006.json"

spec = importlib.util.spec_from_file_location("meta", ROOT / "scripts" / "research-nq-series-metadata-2006.py")
meta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(meta)

pspec = importlib.util.spec_from_file_location("nqpilot", ROOT / "scripts" / "research-nq-parser-pilot.py")
nqpilot = importlib.util.module_from_spec(pspec)
pspec.loader.exec_module(nqpilot)

TARGET = re.compile(r"SELECT SECTOR SPDR|STREETTRACKS|POWERSHARES EXCHANGE TRADED|RYDEX ETF TRUST|PROSHARES", re.I)
SCHEDULE = re.compile(
    r"SCHEDULE OF PORTFOLIO INVESTMENTS|SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS",
    re.I,
)
DOCUMENT_BLOCK = re.compile(r"(?is)<DOCUMENT>(.*?)</DOCUMENT>")
TYPE_NQ = re.compile(r"(?im)^\s*<TYPE>\s*N-Q\b")
FILENAME = re.compile(r"(?im)^\s*<FILENAME>\s*([^\s<]+)")
TEXT_BLOCK = re.compile(r"(?is)<TEXT>(.*)</TEXT>")
STRUCTURED_OR_INCOME = re.compile(r"\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b", re.I)
BROAD_BENCHMARK = re.compile(r"\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", s.upper()).strip()


def visible(raw: str) -> str:
    s = re.sub(r"(?is)<BR\s*/?>", " ", raw)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    return " ".join(html.unescape(s).replace("\xa0", " ").split())


def embedded_primary_nq(submission_text: str) -> tuple[str, str]:
    for dm in DOCUMENT_BLOCK.finditer(submission_text):
        block = dm.group(1)
        if not TYPE_NQ.search(block):
            continue
        filename_m = FILENAME.search(block)
        text_m = TEXT_BLOCK.search(block)
        name = filename_m.group(1).strip() if filename_m else "embedded-nq"
        return name, text_m.group(1) if text_m else block
    return "submission", submission_text


def series_tokens(name: str) -> set[str]:
    stop = {"POWERSHARES", "PROSHARES", "STREETTRACKS", "SPDR", "ETF", "TRUST", "PORTFOLIO", "FUND"}
    return {t for t in norm(name).split() if len(t) >= 3 and t not in stop}


def explicit_series_hits(raw: str, series: list[dict]) -> list[tuple[dict, int]]:
    """Return exact normalized series-name hits and their ending positions in visible text."""
    vis = visible(raw)
    nvis = norm(vis)
    hits: list[tuple[dict, int]] = []
    for s in series:
        name = s.get("seriesName") or ""
        nn = norm(name)
        if not nn:
            continue
        pos = nvis.rfind(nn)
        if pos >= 0:
            hits.append((s, pos + len(nn)))
    return hits


def assign_marker_series(text: str, marker: re.Match, series: list[dict]) -> tuple[dict | None, str]:
    """Assign schedule page using explicit filing-time series names only.

    Holdings/industry words are intentionally excluded from assignment. The nearest
    exact series title before the marker is preferred because N-Q page footers carry
    the current series name, including continuation pages. If absent, a short window
    after the marker can supply a title printed under the schedule heading.
    """
    start = marker.start()
    before = text[max(0, start - 1400):start]
    before_hits = explicit_series_hits(before, series)
    if before_hits:
        # nearest exact occurrence to the marker
        best, _ = max(before_hits, key=lambda x: x[1])
        return best, "EXPLICIT_BEFORE"

    after = text[start:min(len(text), start + 1400)]
    after_hits = explicit_series_hits(after, series)
    if len(after_hits) == 1:
        return after_hits[0][0], "EXPLICIT_AFTER"
    if len(after_hits) > 1:
        # In the forward window choose earliest explicit title.
        vis = visible(after)
        nvis = norm(vis)
        ranked = []
        for s, _ in after_hits:
            nn = norm(s.get("seriesName") or "")
            pos = nvis.find(nn)
            if pos >= 0:
                ranked.append((pos, s))
        if ranked:
            return min(ranked, key=lambda x: x[0])[1], "EXPLICIT_AFTER_EARLIEST"
    return None, "UNASSIGNED"


def grouped_schedule_blocks(text: str, series: list[dict]) -> tuple[dict[str, list[str]], list[dict]]:
    markers = list(SCHEDULE.finditer(text))
    grouped: dict[str, list[str]] = {}
    audit: list[dict] = []
    for j, marker in enumerate(markers):
        start = marker.start()
        end = markers[j + 1].start() if j + 1 < len(markers) else min(len(text), start + 300000)
        block = text[start:end]
        s, rule = assign_marker_series(text, marker, series)
        audit.append({
            "markerIndex": j,
            "marker": visible(marker.group(0)),
            "assignmentRule": rule,
            "seriesId": s.get("seriesId") if s else None,
            "seriesName": s.get("seriesName") if s else None,
        })
        if s and s.get("seriesId"):
            grouped.setdefault(s["seriesId"], []).append(block)
    return grouped, audit


def map_schedule_to_series(block: str, series: list[dict]) -> tuple[dict | None, float]:
    """Deprecated diagnostic fallback retained for old research scripts only.

    Do not use this function for constructing PIT holdings. It can be fooled by
    industry words on continuation pages. New segmentation uses explicit boundaries.
    """
    context = visible(block[:5000])
    c_tokens = set(norm(context).split())
    best = None
    best_score = 0.0
    for s in series:
        name = s.get("seriesName") or ""
        toks = series_tokens(name)
        if not toks:
            continue
        overlap = len(toks & c_tokens) / len(toks)
        exact = norm(name) in norm(context)
        score = 1.0 if exact else overlap
        if score > best_score:
            best, best_score = s, score
    return (best, best_score) if best_score >= 0.60 else (None, best_score)


def parse_segment(text: str) -> tuple[str, int, float]:
    method, _, _, holdings = nqpilot.parse_holdings(text)
    count = len(holdings)
    total_value = sum(max(0.0, float(h.get("marketValue") or 0)) for h in holdings)
    return method, count, total_value


def eligible_name(name: str) -> bool:
    return not STRUCTURED_OR_INCOME.search(name) and not BROAD_BENCHMARK.search(name)


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

    results = []
    for i, x in enumerate(chosen, 1):
        try:
            _, submission = meta.fetch_prefix(meta.sec_url(x["filename"]))
            series = meta.parse_series_contracts(submission, x["company"])
            etf = [s for s in series if s["isEtf"]]
            primary_name, text = embedded_primary_nq(submission)
            markers = list(SCHEDULE.finditer(text))
            grouped, assignment_audit = grouped_schedule_blocks(text, etf)
            by_id = {s.get("seriesId"): s for s in etf if s.get("seriesId")}

            rows = []
            for sid, blocks in grouped.items():
                s = by_id.get(sid)
                if not s:
                    continue
                combined = "\n".join(blocks)
                method, count, total_value = parse_segment(combined)
                rows.append({
                    "seriesId": sid,
                    "seriesName": s.get("seriesName"),
                    "tickers": s.get("etfTickers", []),
                    "assignmentRule": "EXPLICIT_SERIES_BOUNDARY_GROUP",
                    "schedulePages": len(blocks),
                    "parseMethod": method,
                    "parsedHoldings": count,
                    "parsedMarketValueTotal": total_value,
                    "eligibleByName": eligible_name(s.get("seriesName") or ""),
                    "structurallyUsable": bool(10 <= count <= 120 and total_value > 0),
                })

            eligible_rows = [r for r in rows if r["eligibleByName"]]
            usable_eligible = [r for r in eligible_rows if r["structurallyUsable"]]
            r = {
                "company": x["company"],
                "cik": x["cik"],
                "dateFiled": x["dateFiled"],
                "primaryDocument": primary_name,
                "registeredEtfSeries": len(etf),
                "scheduleMarkers": len(markers),
                "assignedScheduleMarkers": sum(1 for a in assignment_audit if a["seriesId"]),
                "unassignedScheduleMarkers": sum(1 for a in assignment_audit if not a["seriesId"]),
                "reportedSeries": len(rows),
                "eligibleReportedSeries": len(eligible_rows),
                "structurallyUsableEligibleSeries": len(usable_eligible),
                "series": rows,
                "assignmentAudit": assignment_audit,
            }
            print(
                f"{i}/{len(chosen)} {x['company'][:42]} registered={len(etf)} schedules={len(markers)} "
                f"assigned={r['assignedScheduleMarkers']} reported={len(rows)} eligible={len(eligible_rows)} usableEligible={len(usable_eligible)}",
                flush=True,
            )
            for row in usable_eligible:
                print("USABLE", json.dumps(row), flush=True)
        except Exception as e:
            r = {"company": x.get("company"), "cik": x.get("cik"), "error": repr(e)}
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}", flush=True)
        results.append(r)

    ok = [r for r in results if "error" not in r]
    reported = sum(r["reportedSeries"] for r in ok)
    eligible = sum(r["eligibleReportedSeries"] for r in ok)
    usable = sum(r["structurallyUsableEligibleSeries"] for r in ok)
    summary = {
        "year": 2006,
        "sampleRule": "One deterministic N-Q filing per known ETF registrant. Schedule pages are assigned only from exact filing-time registered series names nearest each schedule marker; continuation pages are grouped by the same explicit series identity. No holdings-content similarity or return/performance selection.",
        "registrants": len(chosen),
        "fetchSuccess": len(ok),
        "reportedSeries": reported,
        "eligibleReportedSeries": eligible,
        "structurallyUsableEligibleSeries": usable,
        "structurallyUsableEligibleRate": usable / eligible if eligible else None,
        "structuralEligibilityRule": "Same name exclusions as production plus 10 <= grouped parsed holdings <= 120 and positive parsed market value; no returns used.",
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
