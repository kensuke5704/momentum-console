#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "data/research/nq-hybrid-structural-mapping-h1-2006.json"
NPX = ROOT / "data/research/npx-security-master-2006.json"
OUT = ROOT / "data/research/nq-hybrid-country-resolved-h1-2006.json"

RECEIPT = re.compile(
    r"\b(?:ADR|GDR|ADS|AMERICAN\s+DEPOSITARY|GLOBAL\s+DEPOSITARY|DEPOSITARY\s+RECEIPT)S?\b",
    re.I,
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


flat = load("flat_country_v5", ROOT / "scripts/research-sec-submission-header-country-pilot-2006.py")
structural = load("structural_country_v5", ROOT / "scripts/research-nq-npx-structural-mapping-2006.py")


def identity_key(ticker, security_id):
    return ((ticker or "").strip().upper(), (security_id or None))


def non_us_cins(security_id) -> bool:
    value = (security_id or "").strip().upper()
    return len(value) == 9 and value[0].isalpha() and value[0] != "U"


def build_issuer_variants(master: dict):
    out = defaultdict(set)
    for row in master.get("records", []):
        key = identity_key(row.get("ticker"), row.get("securityId"))
        issuer = row.get("issuer") or row.get("normalizedIssuer")
        if issuer:
            out[key].add(str(issuer))
    return out


def exact_historical_resolve(row: dict, master_rows: list[dict]) -> dict:
    """Resolve country only from historical exact issuer-form -> unique CIK -> PIT SEC header.

    Deliberately does not call flat.resolve(), because that helper contains a modern
    current-ticker CIK fallback. Ticker/securityId are carried only as the already
    deterministic N-PX identity key and are never used to discover the issuer CIK.
    """
    report_date = row.get("asOfReportDate")
    forms: list[str] = []
    for issuer in row.get("issuerVariants", []):
        for form in structural.cleaned_forms(str(issuer)):
            if form and form not in forms:
                forms.append(form)

    issuer_rows = [
        x for x in master_rows
        if x.get("form") in flat.base.ISSUER_FORMS
        and report_date
        and x.get("dateFiled") <= report_date
    ]
    attempts = []
    positives = []

    for form in forms:
        target = flat.base.normalize_company(form)
        exact = [x for x in issuer_rows if x.get("normalizedCompany") == target]
        by_cik = defaultdict(list)
        for x in exact:
            by_cik[str(x.get("cik") or "").zfill(10)].append(x)
        attempt = {
            "issuerForm": form,
            "historicalExactCikCount": len(by_cik),
            "historicalExactCiks": sorted(by_cik)[:8],
            "seedSource": "HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME" if len(by_cik) == 1 else None,
        }
        if len(by_cik) != 1:
            attempts.append(attempt)
            continue

        cik = next(iter(by_cik))
        attempt["seedCik"] = cik
        candidates = sorted(by_cik[cik], key=flat.base.filing_sort_key)
        attempt["filingCandidateCount"] = len(candidates)
        filing_attempts = []
        resolved = None
        for filing in candidates[:6]:
            try:
                text, url, status = flat.base.submission_prefix(filing["filename"], 65536)
                acceptance = re.search(r"(?im)^\s*<ACCEPTANCE-DATETIME>\s*(\d{8})", text)
                acceptance_date = (
                    acceptance.group(1)[:4] + "-" + acceptance.group(1)[4:6] + "-" + acceptance.group(1)[6:8]
                    if acceptance else None
                )
                state, historical_name = flat.flat_submission_state(form, cik, text)
                one = {
                    "form": filing.get("form"),
                    "dateFiled": filing.get("dateFiled"),
                    "submissionUrl": url,
                    "httpStatus": status,
                    "acceptanceDate": acceptance_date,
                    "historicalEntityName": historical_name,
                    "stateCode": state,
                }
                filing_attempts.append(one)
                if acceptance_date and acceptance_date > report_date:
                    continue
                if state:
                    resolved = {
                        "classification": "US" if state in flat.old.US_CODES else "NON_US",
                        "stateCode": state,
                        "resolutionSource": "PIT_SUBMISSION_FLAT_HEADER_ENTITY_STATE",
                        "seedSource": "HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME",
                        "seedCik": cik,
                        "issuerForm": form,
                        "evidenceForm": filing.get("form"),
                        "evidenceDateFiled": filing.get("dateFiled"),
                        "acceptanceDate": acceptance_date,
                        "submissionUrl": url,
                        "historicalEntityName": historical_name,
                    }
                    break
            except Exception as exc:
                filing_attempts.append({
                    "form": filing.get("form"),
                    "dateFiled": filing.get("dateFiled"),
                    "error": type(exc).__name__,
                })
        attempt["filingAttempts"] = filing_attempts
        if resolved:
            attempt.update({k: resolved.get(k) for k in (
                "classification", "stateCode", "resolutionSource", "evidenceForm", "evidenceDateFiled", "acceptanceDate"
            )})
            positives.append(resolved)
        attempts.append(attempt)

    classes = sorted({x["classification"] for x in positives})
    if len(classes) > 1:
        raise RuntimeError(
            f"strict historical country conflict {row.get('ticker')} {row.get('securityId')} "
            f"{report_date}: {classes}"
        )
    if len(classes) == 1:
        selected = next(x for x in positives if x["classification"] == classes[0])
        return {**row, **selected, "attempts": attempts}
    return {**row, "classification": "UNKNOWN", "attempts": attempts}


def main() -> None:
    mapping = json.loads(MAPPING.read_text())
    npx = json.loads(NPX.read_text())
    issuers = build_issuer_variants(npx)

    # First pass: same-filing explicit country / deterministic instrument structure only.
    unresolved = {}
    staged = []
    reason_counts = Counter()
    for snapshot in mapping["monthSnapshots"]:
        filings = []
        for filing in snapshot["sourceFilings"]:
            holdings = []
            report_date = filing.get("reportDate")
            for holding in filing.get("holdings", []):
                row = dict(holding)
                classification = "UNKNOWN"
                reason = "UNRESOLVED"
                if row.get("mappingStatus") == "MATCHED_UNIQUE":
                    explicit = row.get("legacyCountryClassification")
                    if explicit in {"US", "NON_US"}:
                        classification = explicit
                        reason = "NQ_EXPLICIT_COUNTRY_SECTION"
                    elif non_us_cins(row.get("mappedSecurityId")):
                        classification = "NON_US"
                        reason = "NON_US_CINS"
                    elif RECEIPT.search(str(row.get("description") or "")):
                        classification = "NON_US"
                        reason = "EXPLICIT_DEPOSITARY_RECEIPT"
                    else:
                        key = identity_key(row.get("mappedTicker"), row.get("mappedSecurityId"))
                        ukey = (key[0], key[1], report_date)
                        unresolved.setdefault(ukey, {
                            "ticker": key[0],
                            "securityId": key[1],
                            "asOfReportDate": report_date,
                            "issuerVariants": sorted(issuers.get(key, set())),
                        })
                row["countryClassification"] = classification
                row["countryReason"] = reason
                reason_counts[reason] += 1
                holdings.append(row)
            filings.append({**{k:v for k,v in filing.items() if k != "holdings"}, "holdings": holdings})
        staged.append({**{k:v for k,v in snapshot.items() if k != "sourceFilings"}, "sourceFilings": filings})

    years = sorted({int(k[2][:4]) for k in unresolved if k[2]})
    master_rows, transports = flat.base.load_master(years) if years else ([], [])
    resolved = {}
    resolution_audit = []
    for key, row in sorted(unresolved.items()):
        result = exact_historical_resolve(row, master_rows) if row.get("issuerVariants") and row.get("asOfReportDate") else {**row, "classification":"UNKNOWN", "attempts":[]}
        resolved[key] = result
        resolution_audit.append(result)
        print("STRICT_COUNTRY", json.dumps({k:result.get(k) for k in (
            "ticker", "securityId", "asOfReportDate", "classification", "seedSource", "seedCik", "issuerForm"
        )}), flush=True)

    # Second pass: promote only exact historical resolutions; all other mapped identities remain UNKNOWN.
    snapshots = []
    for snapshot in staged:
        month_counts = Counter()
        month_weights = defaultdict(float)
        filings = []
        for filing in snapshot["sourceFilings"]:
            report_date = filing.get("reportDate")
            fcounts = Counter(); fweights = defaultdict(float); holdings = []
            for holding in filing.get("holdings", []):
                row = dict(holding)
                classification = row.get("countryClassification", "UNKNOWN")
                if classification == "UNKNOWN" and row.get("mappingStatus") == "MATCHED_UNIQUE":
                    key = identity_key(row.get("mappedTicker"), row.get("mappedSecurityId"))
                    evidence = resolved.get((key[0], key[1], report_date))
                    if evidence and evidence.get("classification") in {"US", "NON_US"}:
                        classification = evidence["classification"]
                        row["countryClassification"] = classification
                        row["countryReason"] = "PIT_SUBMISSION_HEADER_EXACT_HISTORICAL_NAME"
                        row["countryResolutionEvidence"] = evidence
                        reason_counts[row["countryReason"]] += 1
                weight = float(row.get("weight") or 0.0)
                fcounts[classification] += 1; fweights[classification] += weight
                month_counts[classification] += 1; month_weights[classification] += weight
                holdings.append(row)
            filings.append({
                **{k:v for k,v in filing.items() if k not in {"holdings","countryClassificationCounts","countryClassificationWeights"}},
                "countryClassificationCounts": dict(fcounts),
                "countryClassificationWeights": dict(fweights),
                "holdings": holdings,
            })
        snapshots.append({
            **{k:v for k,v in snapshot.items() if k != "sourceFilings"},
            "countryClassificationCounts": dict(month_counts),
            "countryClassificationWeights": dict(month_weights),
            "sourceFilings": filings,
        })

    output = {
        "purpose": (
            "Strict PIT H1 2006 country classification for deterministically mapped COMMON_EQUITY holdings. "
            "Evidence order is same-filing explicit country, deterministic non-US CINS/depositary receipt, then "
            "historical SEC master-index exact issuer-form name only when it identifies exactly one CIK, followed "
            "by a matching pre-report-date complete-submission SEC header. Current ticker metadata, modern issuer "
            "state/country, fuzzy matching, US default, ranks, returns and strategy outcomes are forbidden."
        ),
        "countryEvidenceRule": (
            "NQ_EXPLICIT -> NON_US_CINS/EXPLICIT_RECEIPT -> HISTORICAL_EXACT_ISSUER_FORM_UNIQUE_CIK -> "
            "PIT_SEC_HEADER_STATE -> UNKNOWN"
        ),
        "currentTickerFallbackAllowed": False,
        "currentTickerFallbackCount": 0,
        "masterYears": years,
        "masterIndexTransports": transports,
        "unresolvedInputCount": len(unresolved),
        "resolvedUSCount": sum(x.get("classification") == "US" for x in resolution_audit),
        "resolvedNonUSCount": sum(x.get("classification") == "NON_US" for x in resolution_audit),
        "remainingUnknownCount": sum(x.get("classification") == "UNKNOWN" for x in resolution_audit),
        "reasonCounts": dict(reason_counts),
        "resolutionAudit": resolution_audit,
        "monthSnapshots": snapshots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print("STRICT_COUNTRY_SUMMARY", json.dumps({k:v for k,v in output.items() if k not in {"resolutionAudit","monthSnapshots","masterIndexTransports"}}), flush=True)
    for snapshot in snapshots:
        print("MONTH_COUNTRY", json.dumps({
            "signalMonth": snapshot["signalMonth"],
            "counts": snapshot["countryClassificationCounts"],
            "weights": snapshot["countryClassificationWeights"],
        }), flush=True)


if __name__ == "__main__":
    main()
