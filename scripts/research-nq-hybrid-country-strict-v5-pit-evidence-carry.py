#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = Path(os.environ.get("STRICT_COUNTRY_ACCEPTED_EVIDENCE_DIR", ROOT / "data/research/accepted-country-evidence"))

spec = importlib.util.spec_from_file_location(
    "strict_country_indexed_resolution",
    ROOT / "scripts/research-nq-hybrid-country-strict-v5-indexed-resolution-cache.py",
)
wrapped = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wrapped)
strict = wrapped.strict
base_resolve = wrapped.cached_exact_historical_resolve


def norm_form(value: str | None) -> str:
    return strict.flat.base.normalize_company(str(value or ""))


def strict_evidence_from_row(row: dict) -> list[dict]:
    out = []
    cls = row.get("classification")
    if cls not in {"US", "NON_US"}:
        return out
    nested = row.get("resolutionEvidence") or {}
    candidates = []
    if nested:
        candidates.append((nested, row.get("countryIdentityFormUsed") or nested.get("issuer") or nested.get("historicalEntityName")))
    candidates.append((row, row.get("issuerForm") or row.get("issuer") or row.get("historicalEntityName")))
    for ev, issuer_form in candidates:
        if ev.get("seedSource") != "HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME":
            continue
        if ev.get("resolutionSource") != "PIT_SUBMISSION_FLAT_HEADER_ENTITY_STATE":
            continue
        if not ev.get("seedCik") or not ev.get("stateCode") or not ev.get("evidenceDateFiled"):
            continue
        forms = []
        for raw in [issuer_form, *(row.get("issuerVariants") or [])]:
            if not raw:
                continue
            for cleaned in strict.structural.cleaned_forms(str(raw)):
                n = norm_form(cleaned)
                if n and n not in forms:
                    forms.append(n)
        if not forms:
            continue
        out.append({
            "classification": cls,
            "seedCik": str(ev.get("seedCik")).zfill(10),
            "stateCode": ev.get("stateCode"),
            "resolutionSource": ev.get("resolutionSource"),
            "seedSource": ev.get("seedSource"),
            "issuerForm": issuer_form,
            "evidenceForm": ev.get("evidenceForm"),
            "evidenceDateFiled": ev.get("evidenceDateFiled"),
            "acceptanceDate": ev.get("acceptanceDate"),
            "submissionUrl": ev.get("submissionUrl"),
            "historicalEntityName": ev.get("historicalEntityName"),
            "normalizedForms": forms,
        })
    return out


def iter_rows(data: dict):
    for key in ("resolutionAudit", "identityRows", "rows", "results"):
        value = data.get(key)
        if isinstance(value, list):
            yield from value


_by_form: dict[str, list[dict]] = defaultdict(list)
_source_files = []
if EVIDENCE_DIR.exists():
    for path in sorted(EVIDENCE_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        accepted_here = 0
        for row in iter_rows(data):
            for ev in strict_evidence_from_row(row):
                signature = (ev["classification"], ev["seedCik"], ev["evidenceDateFiled"], ev.get("stateCode"), ev.get("submissionUrl"))
                for form in ev["normalizedForms"]:
                    if not any(
                        (x["classification"], x["seedCik"], x["evidenceDateFiled"], x.get("stateCode"), x.get("submissionUrl")) == signature
                        for x in _by_form[form]
                    ):
                        _by_form[form].append(ev)
                accepted_here += 1
        _source_files.append({"file": str(path), "acceptedEvidenceRows": accepted_here})

pit_reuse_count = 0
fresh_count = 0


def pit_carry_resolve(row: dict, master_rows: list[dict]) -> dict:
    global pit_reuse_count, fresh_count
    report_date = row.get("asOfReportDate")
    if report_date:
        index = wrapped.indexed.ensure_master_index(master_rows)
        positives = []
        checked = []
        forms = []
        for issuer in row.get("issuerVariants", []):
            for cleaned in strict.structural.cleaned_forms(str(issuer)):
                n = norm_form(cleaned)
                if n and n not in forms:
                    forms.append(n)
        for normalized in forms:
            exact = [x for x in index.get(normalized, []) if x.get("dateFiled") and x.get("dateFiled") <= report_date]
            by_cik = defaultdict(list)
            for x in exact:
                by_cik[str(x.get("cik") or "").zfill(10)].append(x)
            checked.append({"normalizedIssuerForm": normalized, "historicalExactCikCount": len(by_cik), "historicalExactCiks": sorted(by_cik)[:8]})
            if len(by_cik) != 1:
                continue
            cik = next(iter(by_cik))
            for ev in _by_form.get(normalized, []):
                if ev["seedCik"] != cik:
                    continue
                if ev["evidenceDateFiled"] > report_date:
                    continue
                acceptance = ev.get("acceptanceDate")
                if acceptance and acceptance > report_date:
                    continue
                positives.append(ev)
        classes = {x["classification"] for x in positives}
        ciks = {x["seedCik"] for x in positives}
        if len(classes) > 1 or len(ciks) > 1:
            raise RuntimeError(f"accepted PIT country evidence conflict for {row.get('ticker')} {row.get('securityId')} {report_date}: classes={sorted(classes)} ciks={sorted(ciks)}")
        if len(classes) == 1 and len(ciks) == 1:
            selected = sorted(positives, key=lambda x: (x["evidenceDateFiled"], x.get("submissionUrl") or ""), reverse=True)[0]
            pit_reuse_count += 1
            return {
                **row,
                **{k:v for k,v in selected.items() if k != "normalizedForms"},
                "attempts": [{"acceptedHistoricalEvidenceCarry": True, "pitMasterReverification": checked}],
                "acceptedEvidenceReuse": True,
                "acceptedEvidenceReusePolicy": "EVIDENCE_DATE_AND_ACCEPTANCE_NOT_AFTER_REPORT_DATE; EXACT_NORMALIZED_ISSUER_FORM_HAS_ONE_CIK_AS_OF_REPORT_DATE; SAME_SEED_CIK",
            }
    fresh_count += 1
    return base_resolve(row, master_rows)


strict.exact_historical_resolve = pit_carry_resolve

if __name__ == "__main__":
    strict.main()
    print("STRICT_COUNTRY_PIT_EVIDENCE_CARRY_SUMMARY", json.dumps({
        "evidenceDirectory": str(EVIDENCE_DIR),
        "evidenceSources": _source_files,
        "indexedAcceptedForms": len(_by_form),
        "pitReusedResolutionCount": pit_reuse_count,
        "freshResolutionCount": fresh_count,
        "freshResolutionCacheSize": len(wrapped._resolution_cache),
        "submissionCacheSize": len(wrapped.indexed._submission_cache),
    }), flush=True)
