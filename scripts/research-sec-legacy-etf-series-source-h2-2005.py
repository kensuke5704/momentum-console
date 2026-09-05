#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/research/sec-complete-portfolio-inventory-h2-2005.json"
PREF = ROOT / "data/research/sec-etf-registrant-operational-prefilter-h1-2006.json"
OUT = ROOT / "data/research/sec-legacy-etf-series-source-h2-2005.json"
ASOF = "2006-01-31"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load_module("catalog_base", ROOT / "scripts/research-sec-historical-etf-series-source-catalog-h1-2006.py")
h2diag = load_module("h2diag", ROOT / "scripts/research-sec-complete-portfolio-title-diagnostic-h2-2005.py")

GENERIC = re.compile(
    r"^(?:ITEM\s+1|SCHEDULES? OF (?:PORTFOLIO )?INVESTMENTS?|PORTFOLIO (?:OF INVESTMENTS|HOLDINGS)|"
    r"STATEMENT OF (?:INVESTMENTS|NET ASSETS)|FORM N Q|QUARTERLY SCHEDULE|REGISTERED MANAGEMENT|"
    r"MANAGEMENT INVESTMENT|SECURITIES AND EXCHANGE|UNITED STATES|WASHINGTON|SHARES?|MARKET|VALUE|"
    r"SECURITY|DESCRIPTION|COMMON STOCKS?|NUMBER|OF SHARES|COUPON|MATURITY|DATE|FACE|AMOUNT|COST|"
    r"SEE NOTES?|TOTAL)\b",
    re.I,
)
DATEISH = re.compile(
    r"\b(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\b|\b2005\b",
    re.I,
)
TITLE_HINT = re.compile(r"\b(?:FUND|ETF|PORTFOLIO|INDEX|TRUST|SPDR|ISHARES|STREETTRACKS|VIPER)\b", re.I)
TITLE_ETF_SEMANTIC = re.compile(r"\b(?:ETF|SPDR|ISHARES|STREETTRACKS|VIPER)\b", re.I)
REGISTRANT_ETF_SEMANTIC = re.compile(r"\b(?:ETF|EXCHANGE[- ]TRADED)\b", re.I)
EXPLICIT_ETF_CLASS_LINE = re.compile(r"\b(?:ETF\s+SHARES?|VIPER(?:\s+SHARES?)?|EXCHANGE[- ]TRADED\s+SHARES?)\b", re.I)
MAX_CLASS_LINE_DISTANCE = 6


def meaningful(line: str) -> bool:
    n = base.norm(line)
    if len(n) < 8 or GENERIC.search(n) or DATEISH.search(n):
        return False
    alpha = sum(ch.isalpha() for ch in line)
    digits = sum(ch.isdigit() for ch in line)
    return alpha >= 5 and digits <= alpha


def title_candidates(window: dict) -> list[dict]:
    lines = window.get("beforeLines", [])[-10:] + window.get("afterLines", [])[:10]
    out: dict[str, dict] = {}
    for i in range(len(lines)):
        for width in (1, 2, 3):
            parts = lines[i:i + width]
            if len(parts) != width or not all(meaningful(x) for x in parts):
                continue
            raw = " ".join(parts)
            n = base.norm(raw)
            if len(n.split()) < 3 or len(n) < 15 or not TITLE_HINT.search(n):
                continue
            out[n] = {"title": raw, "normalizedTitle": n, "lineSpan": width}
    return sorted(
        out.values(),
        key=lambda x: (-len(x["normalizedTitle"].split()), -len(x["normalizedTitle"]), x["normalizedTitle"]),
    )


def complete_prospectus_set(rows: list[dict]) -> list[dict]:
    chosen: dict[str, dict] = {}
    for row in rows:
        if row["form"] in base.CORE and row["dateFiled"] <= ASOF:
            chosen[row["filename"]] = row
    for asof in ("2005-07-31", "2005-08-31", "2005-09-30", "2005-10-31", "2005-11-30", "2005-12-30", ASOF):
        avail = [r for r in rows if r["form"] in base.SUPP and r["dateFiled"] <= asof]
        if avail:
            latest = max(avail, key=lambda r: (r["dateFiled"], r["form"], r["filename"]))
            chosen[latest["filename"]] = latest
    return sorted(chosen.values(), key=lambda r: (r["dateFiled"], r["form"], r["filename"]))


def title_line_occurrences(lines: list[str], normalized_title: str) -> list[int]:
    hits: set[int] = set()
    for i in range(len(lines)):
        for width in (1, 2, 3):
            phrase = base.norm(" ".join(lines[i:i + width]))
            if normalized_title and normalized_title in phrase:
                hits.add(i)
    return sorted(hits)


def classify_binding(title: str, normalized_title: str, registrant: str, prospectus_lines: list[str]) -> tuple[str | None, int | None]:
    occurrences = title_line_occurrences(prospectus_lines, normalized_title)
    if not occurrences:
        return None, None
    marker_lines = [i for i, line in enumerate(prospectus_lines) if EXPLICIT_ETF_CLASS_LINE.search(line)]
    nearest = None
    if marker_lines:
        nearest = min(abs(i - j) for i in occurrences for j in marker_lines)
    if TITLE_ETF_SEMANTIC.search(title):
        return "TITLE_EXPLICIT_ETF_SEMANTIC", nearest
    if REGISTRANT_ETF_SEMANTIC.search(registrant):
        return "REGISTRANT_EXPLICIT_ETF_SEMANTIC", nearest
    if nearest is not None and nearest <= MAX_CLASS_LINE_DISTANCE:
        return "LOCAL_EXPLICIT_ETF_CLASS_WITHIN_6_LINES", nearest
    return None, nearest


def main() -> None:
    inv = json.loads(INV.read_text())
    pref = json.loads(PREF.read_text())
    candidate_ciks = set(pref["positiveCiks"])
    source_rows = [r for r in inv["rows"] if r["cik"] in candidate_ciks and r["dateFiled"] <= ASOF]
    source_rows.sort(key=lambda r: (r["dateFiled"], r["form"], r["cik"], r["filename"]))
    source_ciks = {r["cik"] for r in source_rows}

    prospectus, master_transports = base.load_prospectus(source_ciks)
    ops_by_cik: dict[str, list[dict]] = defaultdict(list)
    prospectus_audit: list[dict] = []
    for cik in sorted(source_ciks):
        for filing in complete_prospectus_set(prospectus.get(cik, [])):
            rec = {**filing, "submissionUrl": base.su(filing["filename"])}
            try:
                text, transport, _, prior = base.ft(rec["submissionUrl"], 4_000_000, 22)
                creation = base.rule.find(base.rule.CREATION, text)
                exchange = base.rule.find(base.rule.EXCHANGE, text)
                lines = h2diag.line_text(text).splitlines()
                rec.update({
                    "transport": transport,
                    "priorErrors": prior,
                    "creationIssuerOwnEvidence": bool(creation),
                    "exchangeIssuerOwnEvidence": bool(exchange),
                    "lineCount": len(lines),
                })
                if creation and exchange:
                    ops_by_cik[cik].append({
                        "dateFiled": filing["dateFiled"],
                        "form": filing["form"],
                        "filename": filing["filename"],
                        "lines": lines,
                    })
            except Exception as exc:
                rec["error"] = type(exc).__name__
                rec["errorDetail"] = str(exc)[:700]
            prospectus_audit.append(rec)

    identities: dict[str, dict] = {}
    filing_audit: list[dict] = []
    rejected_bindings: dict[str, int] = defaultdict(int)

    for row in source_rows:
        rec = {k: row.get(k) for k in ("cik", "company", "form", "dateFiled", "accession", "filename")}
        try:
            submission, transport = h2diag.fetch(row["filename"])
            primary, description, text, doc_type = h2diag.primary_document(submission, row["form"])
            windows = h2diag.marker_windows(text)
            rec.update({
                "transport": transport,
                "primaryDocument": primary,
                "primaryDocumentType": doc_type,
                "documentDescription": description,
                "scheduleMarkerCount": len(windows),
                "hasCompletePortfolioSchedule": bool(windows),
            })
            matches = []
            for window in windows:
                best = None
                for candidate in title_candidates(window):
                    proposals = []
                    for op in ops_by_cik.get(row["cik"], []):
                        if op["dateFiled"] > ASOF:
                            continue
                        binding, distance = classify_binding(
                            candidate["title"], candidate["normalizedTitle"], row["company"], op["lines"]
                        )
                        if not binding:
                            continue
                        proposals.append({
                            **candidate,
                            "binding": binding,
                            "explicitEtfClassLineDistance": distance,
                            "evidenceDateFiled": op["dateFiled"],
                            "evidenceForm": op["form"],
                            "evidenceFilename": op["filename"],
                        })
                    if not proposals:
                        rejected_bindings[candidate["normalizedTitle"]] += 1
                        continue
                    proposal = min(proposals, key=lambda p: (p["evidenceDateFiled"], p["evidenceFilename"], p["binding"]))
                    if best is None or (
                        len(proposal["normalizedTitle"].split()), len(proposal["normalizedTitle"])
                    ) > (
                        len(best["normalizedTitle"].split()), len(best["normalizedTitle"])
                    ):
                        best = proposal
                if not best:
                    continue
                matches.append({**best, "markerIndex": window["markerIndex"]})
                identity_key = f"LEGACY:{row['cik']}:{hashlib.sha1(best['normalizedTitle'].encode()).hexdigest()[:12].upper()}"
                candidate_identity = {
                    "legacyIdentity": identity_key,
                    "cik": row["cik"],
                    "registrant": row["company"],
                    "seriesName": best["title"],
                    "normalizedSeriesName": best["normalizedTitle"],
                    "sourceAccession": row["accession"],
                    "sourceFilingDate": row["dateFiled"],
                    "sourceForm": row["form"],
                    "sourceFilename": row["filename"],
                    "evidenceDateFiled": best["evidenceDateFiled"],
                    "evidenceForm": best["evidenceForm"],
                    "evidenceFilename": best["evidenceFilename"],
                    "binding": best["binding"],
                    "explicitEtfClassLineDistance": best["explicitEtfClassLineDistance"],
                }
                current = identities.get(identity_key)
                if current is None or (
                    candidate_identity["sourceFilingDate"], candidate_identity["sourceAccession"] or ""
                ) > (
                    current["sourceFilingDate"], current["sourceAccession"] or ""
                ):
                    identities[identity_key] = candidate_identity
            rec["matchedMarkerCount"] = len(matches)
            rec["matchedLegacySeriesNames"] = sorted({m["normalizedTitle"] for m in matches})
            rec["matches"] = matches
        except Exception as exc:
            rec["error"] = type(exc).__name__
            rec["errorDetail"] = str(exc)[:900]
        filing_audit.append(rec)
        print("SOURCE", json.dumps({
            "cik": row["cik"], "company": row["company"], "form": row["form"],
            "dateFiled": row["dateFiled"], "markers": rec.get("scheduleMarkerCount"),
            "matchedMarkers": rec.get("matchedMarkerCount"), "series": len(rec.get("matchedLegacySeriesNames", [])),
            "error": rec.get("error"),
        }), flush=True)

    legacy = sorted(identities.values(), key=lambda x: (x["cik"], x["normalizedSeriesName"]))
    binding_counts: dict[str, int] = defaultdict(int)
    for item in legacy:
        binding_counts[item["binding"]] += 1

    # The latest public complete-portfolio report per contemporaneous identity is selected.
    # Amendments with no accepted schedule never enter identities and therefore cannot supersede a base report.
    january = sorted(
        [x for x in legacy if x["sourceFilingDate"] <= ASOF and x["evidenceDateFiled"] <= ASOF],
        key=lambda x: (x["cik"], x["normalizedSeriesName"]),
    )

    out = {
        "purpose": (
            "Strict pre-Series-ID ETF source identities for 2005 H2 complete-portfolio filings. Because SEC "
            "Series/Class IDs were not mandatory until 2006-02-06, identities use only contemporaneous Fund/Series "
            "titles printed at accepted N-Q/N-CSR/N-CSRS complete-portfolio schedule boundaries. Each title must "
            "also bind at Series level inside a same-CIK prospectus that independently contains issuer-own Creation "
            "Unit plus exchange-listing/trading evidence and was public by 2006-01-31. Series-level binding is "
            "accepted only when the title itself is explicitly ETF-semantic, the registrant legal name explicitly "
            "states ETF/Exchange-Traded, or the exact title occurs within six lines of an explicit ETF/VIPER Shares "
            "label. The six-line limit is frozen from document-structure separation observed in the line-binding "
            "diagnostic, not from holdings or strategy outcomes. Amendments supersede holdings only if their own "
            "primary filing document contains an accepted complete-portfolio schedule. Later Series IDs, holdings "
            "outcomes, ranks, returns, and strategy results are not used."
        ),
        "source": "PRE_SERIES_ID_H2_COMPLETE_PORTFOLIO_STRICT_SERIES_BINDING_V2",
        "seriesIdMandatoryDate": "2006-02-06",
        "asOf": ASOF,
        "candidateRegistrantCount": len(candidate_ciks),
        "candidateCompletePortfolioFilingCount": len(source_rows),
        "candidateRegistrantWithFilingCount": len(source_ciks),
        "operationalEvidenceFilingCount": sum(len(v) for v in ops_by_cik.values()),
        "legacyPositiveRegistrantCount": len({x["cik"] for x in legacy}),
        "legacyPositiveSeriesCount": len(legacy),
        "januarySourceSeriesCount": len(january),
        "bindingCounts": dict(sorted(binding_counts.items())),
        "legacySeries": legacy,
        "januarySourceSeries": january,
        "sourceFilingNoScheduleCount": sum(not x.get("hasCompletePortfolioSchedule", False) and "error" not in x for x in filing_audit),
        "amendmentNoScheduleCount": sum(str(x.get("form", "")).endswith("/A") and not x.get("hasCompletePortfolioSchedule", False) and "error" not in x for x in filing_audit),
        "prospectusErrorCount": sum("error" in x for x in prospectus_audit),
        "sourceFilingErrorCount": sum("error" in x for x in filing_audit),
        "masterTransports": master_transports,
        "prospectusAudit": prospectus_audit,
        "sourceFilingAudit": filing_audit,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k not in (
        "legacySeries", "januarySourceSeries", "masterTransports", "prospectusAudit", "sourceFilingAudit"
    )}), flush=True)


if __name__ == "__main__":
    main()
