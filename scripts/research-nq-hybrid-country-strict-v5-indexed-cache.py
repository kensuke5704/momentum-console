#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "strict_country_base_indexed",
    ROOT / "scripts/research-nq-hybrid-country-strict-v5-h1-2006.py",
)
strict = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(strict)

# Exact transport cache only: same SEC submission filename + byte limit -> same bytes.
_orig_submission_prefix = strict.flat.base.submission_prefix
_submission_cache: dict[tuple[str, int], tuple] = {}


def cached_submission_prefix(filename: str, max_bytes: int):
    key = (filename, int(max_bytes))
    if key not in _submission_cache:
        _submission_cache[key] = _orig_submission_prefix(filename, max_bytes)
    return _submission_cache[key]


strict.flat.base.submission_prefix = cached_submission_prefix

# The base implementation repeatedly scans every SEC master row for every
# (ticker, securityId, reportDate). Build the exact same eligible-row universe once,
# indexed only by the already-used normalizedCompany key. Date and unique-CIK tests
# remain identical inside each resolution call.
_master_object_id: int | None = None
_master_by_normalized_company: dict[str, list[dict]] = {}


def ensure_master_index(master_rows: list[dict]) -> dict[str, list[dict]]:
    global _master_object_id, _master_by_normalized_company
    oid = id(master_rows)
    if _master_object_id != oid:
        by: dict[str, list[dict]] = defaultdict(list)
        for row in master_rows:
            if row.get("form") in strict.flat.base.ISSUER_FORMS:
                by[str(row.get("normalizedCompany") or "")].append(row)
        _master_by_normalized_company = dict(by)
        _master_object_id = oid
        print(
            "STRICT_COUNTRY_MASTER_INDEX",
            json.dumps({
                "masterRowCount": len(master_rows),
                "indexedNormalizedCompanyCount": len(_master_by_normalized_company),
                "indexedIssuerFormRowCount": sum(len(v) for v in _master_by_normalized_company.values()),
            }),
            flush=True,
        )
    return _master_by_normalized_company


def indexed_exact_historical_resolve(row: dict, master_rows: list[dict]) -> dict:
    report_date = row.get("asOfReportDate")
    forms: list[str] = []
    for issuer in row.get("issuerVariants", []):
        for form in strict.structural.cleaned_forms(str(issuer)):
            if form and form not in forms:
                forms.append(form)

    index = ensure_master_index(master_rows)
    attempts = []
    positives = []

    for form in forms:
        target = strict.flat.base.normalize_company(form)
        # Semantically identical to:
        # [x for x in master_rows if x.form in ISSUER_FORMS and
        #  x.dateFiled <= report_date and x.normalizedCompany == target]
        exact = [
            x for x in index.get(target, [])
            if report_date and x.get("dateFiled") <= report_date
        ]
        by_cik: dict[str, list[dict]] = defaultdict(list)
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
        candidates = sorted(by_cik[cik], key=strict.flat.base.filing_sort_key)
        attempt["filingCandidateCount"] = len(candidates)
        filing_attempts = []
        resolved = None
        for filing in candidates[:6]:
            try:
                text, url, status = strict.flat.base.submission_prefix(filing["filename"], 65536)
                acceptance = re.search(r"(?im)^\s*<ACCEPTANCE-DATETIME>\s*(\d{8})", text)
                acceptance_date = (
                    acceptance.group(1)[:4] + "-" + acceptance.group(1)[4:6] + "-" + acceptance.group(1)[6:8]
                    if acceptance else None
                )
                state, historical_name = strict.flat.flat_submission_state(form, cik, text)
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
                        "classification": "US" if state in strict.flat.old.US_CODES else "NON_US",
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
                "classification", "stateCode", "resolutionSource", "evidenceForm",
                "evidenceDateFiled", "acceptanceDate",
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


strict.exact_historical_resolve = indexed_exact_historical_resolve

if __name__ == "__main__":
    strict.main()
    print(
        "STRICT_COUNTRY_INDEXED_CACHE_SUMMARY",
        json.dumps({
            "submissionCacheSize": len(_submission_cache),
            "masterIndexedCompanyCount": len(_master_by_normalized_company),
        }),
        flush=True,
    )
