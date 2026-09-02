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


def map_schedule_to_series(context_block: str, series: list[dict]) -> tuple[dict | None, float]:
    # N-Q series/fund headings frequently appear immediately BEFORE the generic
    # "Schedule of Investments" heading. The caller therefore supplies a tight
    # window spanning both sides of that marker. Refuse ties/near-ties rather
    # than forcing a series assignment.
    context = visible(context_block)
    normalized_context = norm(context)
    c_tokens = set(normalized_context.split())
    ranked = []
    for s in series:
        name = s.get("seriesName") or ""
        toks = series_tokens(name)
        if not toks:
            continue
        exact = norm(name) in normalized_context
        overlap = len(toks & c_tokens) / len(toks)
        ranked.append((1.0 if exact else overlap, bool(exact), s))
    ranked.sort(key=lambda x: (x[0], x[1], x[2].get("seriesName") or ""), reverse=True)
    if not ranked or ranked[0][0] < 0.60:
        return None, ranked[0][0] if ranked else 0.0
    best_score, best_exact, best = ranked[0]
    if len(ranked) > 1:
        second_score, second_exact, _ = ranked[1]
        if best_score == second_score and best_exact == second_exact:
            return None, best_score
        if not best_exact and best_score - second_score < 0.15:
            return None, best_score
    return best, best_score


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

            mapped: dict[str, dict] = {}
            unmapped_blocks = 0
            for j, marker in enumerate(markers):
                start = marker.start()
                end = markers[j + 1].start() if j + 1 < len(markers) else min(len(text), start + 300000)
                block = text[start:end]
                mapping_context = text[max(0, start - 5000):min(end, start + 2500)]
                s, score = map_schedule_to_series(mapping_context, etf)
                if not s or not s.get("seriesId"):
                    unmapped_blocks += 1
                    continue
                method, count, total_value = parse_segment(block)
                candidate = {
                    "seriesId": s.get("seriesId"),
                    "seriesName": s.get("seriesName"),
                    "tickers": s.get("etfTickers", []),
                    "mappingScore": score,
                    "parseMethod": method,
                    "parsedHoldings": count,
                    "parsedMarketValueTotal": total_value,
                    "eligibleByName": eligible_name(s.get("seriesName") or ""),
                    "structurallyUsable": bool(10 <= count <= 120 and total_value > 0),
                }
                current = mapped.get(s["seriesId"])
                if current is None or (count, score) > (current["parsedHoldings"], current["mappingScore"]):
                    mapped[s["seriesId"]] = candidate

            rows = list(mapped.values())
            eligible_rows = [r for r in rows if r["eligibleByName"]]
            usable_eligible = [r for r in eligible_rows if r["structurallyUsable"]]
            r = {
                "company": x["company"],
                "cik": x["cik"],
                "dateFiled": x["dateFiled"],
                "primaryDocument": primary_name,
                "registeredEtfSeries": len(etf),
                "scheduleMarkers": len(markers),
                "unmappedScheduleBlocks": unmapped_blocks,
                "reportedSeries": len(rows),
                "eligibleReportedSeries": len(eligible_rows),
                "structurallyUsableEligibleSeries": len(usable_eligible),
                "series": rows,
            }
            print(f"{i}/{len(chosen)} {x['company'][:42]} registered={len(etf)} schedules={len(markers)} reported={len(rows)} eligible={len(eligible_rows)} usableEligible={len(usable_eligible)}", flush=True)
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
        "sampleRule": "One deterministic N-Q filing per known ETF registrant; schedules mapped to filing-time registered series using tight pre/post-heading context; ambiguous ties rejected; no return/performance selection.",
        "registrants": len(chosen),
        "fetchSuccess": len(ok),
        "reportedSeries": reported,
        "eligibleReportedSeries": eligible,
        "structurallyUsableEligibleSeries": usable,
        "structurallyUsableEligibleRate": usable / eligible if eligible else None,
        "structuralEligibilityRule": "Same name exclusions as production plus 10 <= parsed holdings <= 120 and positive parsed market value; no returns used.",
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
