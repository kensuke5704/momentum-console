#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/research/sec-marketwide-nq-lookback-q4-2005.json"
PREF = ROOT / "data/research/sec-etf-registrant-operational-prefilter-h1-2006.json"
OUT = ROOT / "data/research/sec-legacy-etf-series-source-q4-2005.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load_module("catalog_base", ROOT / "scripts/research-sec-historical-etf-series-source-catalog-h1-2006.py")
diag = load_module("legacy_diag", ROOT / "scripts/research-nq-legacy-series-title-diagnostic-q4-2005.py")

GENERIC = re.compile(
    r"^(?:ITEM\s+1|SCHEDULES? OF (?:PORTFOLIO )?INVESTMENTS?|PORTFOLIO (?:OF INVESTMENTS|HOLDINGS)|"
    r"STATEMENT OF INVESTMENTS|FORM N Q|QUARTERLY SCHEDULE|REGISTERED MANAGEMENT|MANAGEMENT INVESTMENT|"
    r"SECURITIES AND EXCHANGE|UNITED STATES|WASHINGTON|SHARES?|MARKET|VALUE|SECURITY|DESCRIPTION|"
    r"COMMON STOCKS?|NUMBER|OF SHARES|COUPON|MATURITY|DATE|FACE|AMOUNT|COST|SEE NOTES?|TOTAL)\b",
    re.I,
)
DATEISH = re.compile(r"\b(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\b|\b2005\b", re.I)
TITLE_HINT = re.compile(r"\b(?:FUND|ETF|PORTFOLIO|INDEX|TRUST|SPDR|ISHARES|STREETTRACKS|VIPER)\b", re.I)


def complete_prospectus_set(rows: list[dict]) -> list[dict]:
    chosen = {}
    for row in rows:
        if row["form"] in base.CORE and row["dateFiled"] <= "2006-01-31":
            chosen[row["filename"]] = row
    # 497 supplements are numerous. At each month end through January, keep the latest
    # public supplement; dedupe across cutoffs. Core filings are all retained because a
    # mixed trust can file separate amendments for different Series.
    for asof in ("2005-10-31", "2005-11-30", "2005-12-30", "2006-01-31"):
        avail = [r for r in rows if r["form"] in base.SUPP and r["dateFiled"] <= asof]
        if avail:
            latest = max(avail, key=lambda r: (r["dateFiled"], r["form"], r["filename"]))
            chosen[latest["filename"]] = latest
    return sorted(chosen.values(), key=lambda r: (r["dateFiled"], r["form"], r["filename"]))


def meaningful(line: str) -> bool:
    n = base.norm(line)
    if len(n) < 8 or GENERIC.search(n) or DATEISH.search(n):
        return False
    alpha = sum(ch.isalpha() for ch in line)
    digits = sum(ch.isdigit() for ch in line)
    if alpha < 5 or digits > alpha:
        return False
    return True


def title_candidates(window: dict) -> list[dict]:
    # Closest explicit lines around each schedule heading. Contiguous 1-3 line phrases
    # allow old stylized headings such as "iSHARES" + "... INDEX FUND" while keeping
    # every candidate auditable from the filing text itself.
    lines = window.get("beforeLines", [])[-10:] + window.get("afterLines", [])[:10]
    out = {}
    for i in range(len(lines)):
        for width in (1, 2, 3):
            parts = lines[i:i + width]
            if len(parts) != width or not all(meaningful(x) for x in parts):
                continue
            raw = " ".join(parts)
            n = base.norm(raw)
            words = n.split()
            if len(words) < 3 or len(n) < 15 or not TITLE_HINT.search(n):
                continue
            out[n] = {"title": raw, "normalizedTitle": n, "lineSpan": width}
    return sorted(out.values(), key=lambda x: (-len(x["normalizedTitle"].split()), -len(x["normalizedTitle"]), x["normalizedTitle"]))


def main() -> None:
    inv = json.loads(INV.read_text())
    pref = json.loads(PREF.read_text())
    ciks = set(pref["positiveCiks"])
    q4_rows = [row for row in inv["rows"] if row["cik"] in ciks]
    q4_ciks = {row["cik"] for row in q4_rows}
    prospectus, master_transports = base.load_prospectus(q4_ciks)

    ops_by_cik: dict[str, list[dict]] = defaultdict(list)
    prospectus_audit = []
    for cik in sorted(q4_ciks):
        for filing in complete_prospectus_set(prospectus.get(cik, [])):
            rec = {**filing, "submissionUrl": base.su(filing["filename"])}
            try:
                text, transport, _, prior = base.ft(rec["submissionUrl"], 4_000_000, 22)
                creation = base.rule.find(base.rule.CREATION, text)
                exchange = base.rule.find(base.rule.EXCHANGE, text)
                rec["transport"] = transport
                rec["priorErrors"] = prior
                rec["creationIssuerOwnEvidence"] = bool(creation)
                rec["exchangeIssuerOwnEvidence"] = bool(exchange)
                if creation and exchange:
                    ctx = base.norm(base.context(text, creation, exchange))
                    ops_by_cik[cik].append({
                        "dateFiled": filing["dateFiled"],
                        "form": filing["form"],
                        "filename": filing["filename"],
                        "contextNorm": ctx,
                    })
            except Exception as exc:
                rec["error"] = type(exc).__name__
                rec["errorDetail"] = str(exc)[:700]
            prospectus_audit.append(rec)

    identities = {}
    filing_audit = []
    for row in q4_rows:
        rec = {k: row[k] for k in ("cik", "company", "dateFiled", "accession", "filename")}
        try:
            submission, transport = diag.fetch(row["filename"])
            primary, description, text = diag.primary_nq(submission)
            windows = diag.marker_windows(text)
            rec.update({
                "transport": transport,
                "primaryDocument": primary,
                "documentDescription": description,
                "scheduleMarkerCount": len(windows),
            })
            matches = []
            for window in windows:
                candidates = title_candidates(window)
                best = None
                for candidate in candidates:
                    matching_ops = [
                        op for op in ops_by_cik.get(row["cik"], [])
                        if op["dateFiled"] <= "2006-01-31" and candidate["normalizedTitle"] in op["contextNorm"]
                    ]
                    if not matching_ops:
                        continue
                    earliest = min(matching_ops, key=lambda op: (op["dateFiled"], op["filename"]))
                    proposal = {
                        **candidate,
                        "markerIndex": window["markerIndex"],
                        "evidenceDateFiled": earliest["dateFiled"],
                        "evidenceForm": earliest["form"],
                        "evidenceFilename": earliest["filename"],
                    }
                    if best is None or (
                        len(proposal["normalizedTitle"].split()), len(proposal["normalizedTitle"])
                    ) > (
                        len(best["normalizedTitle"].split()), len(best["normalizedTitle"])
                    ):
                        best = proposal
                if best:
                    matches.append(best)
                    identity_key = f"LEGACY:{row['cik']}:{hashlib.sha1(best['normalizedTitle'].encode()).hexdigest()[:12].upper()}"
                    current = identities.get(identity_key)
                    candidate_identity = {
                        "legacyIdentity": identity_key,
                        "cik": row["cik"],
                        "registrant": row["company"],
                        "seriesName": best["title"],
                        "normalizedSeriesName": best["normalizedTitle"],
                        "sourceAccession": row["accession"],
                        "sourceFilingDate": row["dateFiled"],
                        "sourceFilename": row["filename"],
                        "evidenceDateFiled": best["evidenceDateFiled"],
                        "evidenceForm": best["evidenceForm"],
                        "evidenceFilename": best["evidenceFilename"],
                        "binding": "PRE_SERIES_ID_EXPLICIT_NQ_TITLE_PLUS_ISSUER_OWN_EVIDENCE",
                    }
                    if current is None or (
                        candidate_identity["sourceFilingDate"], candidate_identity["sourceAccession"]
                    ) > (
                        current["sourceFilingDate"], current["sourceAccession"]
                    ):
                        identities[identity_key] = candidate_identity
            rec["matchedMarkerCount"] = len(matches)
            rec["matchedLegacySeriesNames"] = sorted({m["normalizedTitle"] for m in matches})
            rec["matches"] = matches
        except Exception as exc:
            rec["error"] = type(exc).__name__
            rec["errorDetail"] = str(exc)[:900]
        filing_audit.append(rec)
        print("NQ", json.dumps({
            "cik": row["cik"], "company": row["company"], "dateFiled": row["dateFiled"],
            "markers": rec.get("scheduleMarkerCount"), "matchedMarkers": rec.get("matchedMarkerCount"),
            "series": len(rec.get("matchedLegacySeriesNames", [])), "error": rec.get("error")
        }), flush=True)

    legacy = sorted(identities.values(), key=lambda x: (x["cik"], x["normalizedSeriesName"]))
    january = [x for x in legacy if x["sourceFilingDate"] <= "2006-01-31" and x["evidenceDateFiled"] <= "2006-01-31"]
    out = {
        "purpose": (
            "Strict pre-Series-ID ETF source identities for Q4 2005 N-Q filings. SEC Series/Class identifiers "
            "were not mandatory until 2006-02-06, so this resolver uses only explicit Series/Fund titles printed "
            "around the N-Q schedule heading and requires an exact normalized title match inside a same-CIK "
            "prospectus context that independently contains issuer-own Creation Unit plus exchange evidence and "
            "was public by 2006-01-31. Later Series IDs, holdings outcomes, ranks, returns, and strategy results are "
            "not used. Synthetic legacyIdentity keys are hashes of CIK + contemporaneous normalized title, not "
            "backfilled SEC Series IDs."
        ),
        "source": "PRE_SERIES_ID_EXPLICIT_NQ_TITLE_STRICT_ETF_SOURCE_V1",
        "seriesIdMandatoryDate": "2006-02-06",
        "candidateRegistrantCount": len(ciks),
        "q4CandidateRegistrantCount": len(q4_ciks),
        "q4CandidateFilingCount": len(q4_rows),
        "operationalEvidenceFilingCount": sum(len(v) for v in ops_by_cik.values()),
        "legacyPositiveRegistrantCount": len({x["cik"] for x in legacy}),
        "legacyPositiveSeriesCount": len(legacy),
        "januarySourceSeriesCount": len(january),
        "legacySeries": legacy,
        "januarySourceSeries": january,
        "prospectusErrorCount": sum("error" in x for x in prospectus_audit),
        "nqErrorCount": sum("error" in x for x in filing_audit),
        "masterTransports": master_transports,
        "prospectusAudit": prospectus_audit,
        "nqAudit": filing_audit,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "q4CandidateRegistrantCount": out["q4CandidateRegistrantCount"],
        "q4CandidateFilingCount": out["q4CandidateFilingCount"],
        "operationalEvidenceFilingCount": out["operationalEvidenceFilingCount"],
        "legacyPositiveRegistrantCount": out["legacyPositiveRegistrantCount"],
        "legacyPositiveSeriesCount": out["legacyPositiveSeriesCount"],
        "januarySourceSeriesCount": out["januarySourceSeriesCount"],
        "prospectusErrorCount": out["prospectusErrorCount"],
        "nqErrorCount": out["nqErrorCount"],
    }), flush=True)


if __name__ == "__main__":
    main()
