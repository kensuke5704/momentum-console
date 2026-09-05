#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/research/sec-complete-portfolio-inventory-h1-2006.json"
PREF = ROOT / "data/research/sec-etf-registrant-operational-prefilter-h1-2006.json"
MANDATORY = "2006-02-06"
ASOF = "2006-06-30"
MONTH_ENDS = ["2006-02-28", "2006-03-31", "2006-04-28", "2006-05-31", "2006-06-30"]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load_module("catalog_base", ROOT / "scripts/research-sec-historical-etf-series-source-catalog-h1-2006.py")
h2diag = load_module("h2diag", ROOT / "scripts/research-sec-complete-portfolio-title-diagnostic-h2-2005.py")

TITLE_ETF = re.compile(r"\b(?:ETF|SPDR|ISHARES|STREETTRACKS|VIPER)\b", re.I)
REGISTRANT_ETF = re.compile(r"\b(?:ETF|EXCHANGE[- ]TRADED)\b", re.I)
ETF_CLASS = re.compile(r"\b(?:ETF\s+SHARES?|VIPER(?:\s+SHARES?)?|EXCHANGE[- ]TRADED(?:\s+SHARES?)?)\b", re.I)
MAX_LINE_DISTANCE = 6


def complete_prospectus_set(rows: list[dict]) -> list[dict]:
    chosen: dict[str, dict] = {}
    for r in rows:
        if r["form"] in base.CORE and MANDATORY <= r["dateFiled"] <= ASOF:
            chosen[r["filename"]] = r
    for asof in MONTH_ENDS:
        avail = [r for r in rows if r["form"] in base.SUPP and MANDATORY <= r["dateFiled"] <= asof]
        if avail:
            latest = max(avail, key=lambda r: (r["dateFiled"], r["form"], r["filename"]))
            chosen[latest["filename"]] = latest
    return sorted(chosen.values(), key=lambda r: (r["dateFiled"], r["form"], r["filename"]))


def title_occurrences(lines: list[str], title: str) -> list[int]:
    target = base.norm(title)
    if not target:
        return []
    hits: set[int] = set()
    for i in range(len(lines)):
        for width in (1, 2, 3):
            phrase = base.norm(" ".join(lines[i:i+width]))
            if target in phrase:
                hits.add(i)
    return sorted(hits)


def bind_series(series: dict, registrant: str, lines: list[str], series_count: int) -> tuple[str | None, int | None]:
    explicit_class = any(ETF_CLASS.search(c.get("className") or "") for c in series.get("classes", []))
    if explicit_class:
        return "EXPLICIT_ETF_CLASS_METADATA", 0
    if TITLE_ETF.search(series.get("seriesName") or ""):
        return "SERIES_TITLE_EXPLICIT_ETF_SEMANTIC", None
    if REGISTRANT_ETF.search(registrant or ""):
        return "REGISTRANT_EXPLICIT_ETF_SEMANTIC", None
    if series_count == 1:
        return "SINGLE_SERIES_FILING_WITH_ISSUER_OWN_EVIDENCE", None
    occurrences = title_occurrences(lines, series.get("seriesName") or "")
    marker_lines = [i for i, line in enumerate(lines) if ETF_CLASS.search(line)]
    nearest = min((abs(i-j) for i in occurrences for j in marker_lines), default=None)
    if nearest is not None and nearest <= MAX_LINE_DISTANCE:
        return "LOCAL_EXPLICIT_ETF_CLASS_WITHIN_6_LINES", nearest
    return None, nearest


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--shard", type=int, required=True); ap.add_argument("--shards", type=int, default=4)
    args = ap.parse_args()
    inv = json.loads(INV.read_text()); pref = json.loads(PREF.read_text())
    all_ciks = sorted(set(pref["positiveCiks"])); assigned = [c for i,c in enumerate(all_ciks) if i % args.shards == args.shard]
    assigned_set = set(assigned)
    pros, master_transports = base.load_prospectus(assigned_set)

    evidence: list[dict] = []; prospectus_audit: list[dict] = []
    for cik in assigned:
        for filing in complete_prospectus_set(pros.get(cik, [])):
            rec = {**filing, "indexUrl": base.iu(filing["filename"]), "submissionUrl": base.su(filing["filename"])}
            try:
                series, itr, iprior = base.parse_index_series(rec["indexUrl"])
                text, strans, _, sprior = base.ft(rec["submissionUrl"], 5_000_000, 24)
                creation = base.rule.find(base.rule.CREATION, text); exchange = base.rule.find(base.rule.EXCHANGE, text)
                lines = h2diag.line_text(text).splitlines()
                rec.update({"indexTransport": itr, "indexPriorErrors": iprior, "indexSeriesCount": len(series), "submissionTransport": strans, "submissionPriorErrors": sprior, "creationIssuerOwnEvidence": bool(creation), "exchangeIssuerOwnEvidence": bool(exchange)})
                positives = []
                if creation and exchange:
                    for s in series:
                        binding, distance = bind_series(s, filing["company"], lines, len(series))
                        if binding:
                            item = {"cik": cik, "registrant": filing["company"], "seriesId": s["seriesId"], "seriesName": s.get("seriesName") or "", "classes": s.get("classes", []), "evidenceDateFiled": filing["dateFiled"], "evidenceForm": filing["form"], "evidenceFilename": filing["filename"], "binding": binding, "explicitEtfClassLineDistance": distance}
                            positives.append(item); evidence.append(item)
                rec["positiveSeriesCount"] = len(positives); rec["positiveSeriesIds"] = [x["seriesId"] for x in positives]
            except Exception as exc:
                rec["error"] = type(exc).__name__; rec["errorDetail"] = str(exc)[:700]
            prospectus_audit.append(rec)
            print("PROSPECTUS", json.dumps({k:rec.get(k) for k in ("cik","form","dateFiled","indexSeriesCount","creationIssuerOwnEvidence","exchangeIssuerOwnEvidence","positiveSeriesCount","error")}), flush=True)

    first: dict[str, dict] = {}
    for r in sorted(evidence, key=lambda x: (x["evidenceDateFiled"], x["seriesId"], x["evidenceFilename"])):
        if r["seriesId"] not in first:
            first[r["seriesId"]] = r
    positive_ids = set(first)

    source_occurrences: list[dict] = []; source_audit: list[dict] = []
    rows = [r for r in inv["rows"] if r["cik"] in assigned_set and MANDATORY <= r["dateFiled"] <= ASOF]
    for row in rows:
        rec = {k:row.get(k) for k in ("cik","company","form","dateFiled","filename","accession","indexUrl")}
        try:
            series, itr, iprior = base.parse_index_series(row["indexUrl"])
            submission, transport = h2diag.fetch(row["filename"])
            primary, description, text, doc_type = h2diag.primary_document(submission, row["form"])
            windows = h2diag.marker_windows(text)
            rec.update({"indexTransport":itr,"indexPriorErrors":iprior,"indexSeriesCount":len(series),"transport":transport,"primaryDocument":primary,"primaryDocumentType":doc_type,"documentDescription":description,"scheduleMarkerCount":len(windows),"hasCompletePortfolioSchedule":bool(windows)})
            if windows:
                for s in series:
                    if s["seriesId"] in positive_ids and first[s["seriesId"]]["evidenceDateFiled"] <= row["dateFiled"]:
                        source_occurrences.append({**row,"seriesId":s["seriesId"],"seriesName":s.get("seriesName") or first[s["seriesId"]]["seriesName"],"evidenceDateFiled":first[s["seriesId"]]["evidenceDateFiled"],"binding":first[s["seriesId"]]["binding"]})
            rec["positiveSeriesIds"] = [s["seriesId"] for s in series if s["seriesId"] in positive_ids]
        except Exception as exc:
            rec["error"] = type(exc).__name__; rec["errorDetail"] = str(exc)[:700]
        source_audit.append(rec)
        print("SOURCE",json.dumps({k:rec.get(k) for k in ("cik","form","dateFiled","indexSeriesCount","scheduleMarkerCount","error")}),flush=True)

    out = {
        "purpose":"Production-independent post-2006-02-06 strict Series-ID ETF source shard. Positive Series IDs require same-filing issuer-own Creation Unit plus exchange-listing/trading evidence and Series-level binding by explicit ETF/VIPER class metadata, explicit ETF-semantic Series title or registrant legal name, single-Series filing, or exact Series title within six lines of an explicit ETF/VIPER Shares label. Trust-global context inheritance is prohibited. Source filings are N-Q/N-CSR/N-CSRS complete-portfolio forms and amendments; an amendment is a holdings source only if its own primary document contains an accepted schedule. No holdings outcomes, ranks, returns, or strategy results are used.",
        "shard":args.shard,"shards":args.shards,"assignedRegistrantCount":len(assigned),"assignedCiks":assigned,
        "positiveSeriesCount":len(first),"positiveSeries":sorted(first.values(),key=lambda x:x["seriesId"]),
        "sourceOccurrenceCount":len(source_occurrences),"sourceOccurrences":source_occurrences,
        "prospectusErrorCount":sum("error" in x for x in prospectus_audit),"sourceErrorCount":sum("error" in x for x in source_audit),
        "sourceNoScheduleCount":sum("error" not in x and not x.get("hasCompletePortfolioSchedule",False) for x in source_audit),
        "prospectusAudit":prospectus_audit,"sourceAudit":source_audit,"masterTransports":master_transports,
    }
    path=ROOT/"data"/"research"/f"sec-id-era-strict-series-source-h1-2006-shard-{args.shard}.json"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(out,indent=2)+"\n")
    print("SUMMARY",json.dumps({k:v for k,v in out.items() if k not in ("positiveSeries","sourceOccurrences","prospectusAudit","sourceAudit","masterTransports","assignedCiks")}),flush=True)


if __name__ == "__main__": main()
