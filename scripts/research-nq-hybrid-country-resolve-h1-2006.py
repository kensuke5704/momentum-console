#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/research/nq-hybrid-country-cache-h1-2006.json"
OUT = ROOT / "data/research/nq-hybrid-country-resolved-h1-2006.json"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


flat = load("flat", ROOT / "scripts/research-sec-submission-header-country-pilot-2006.py")
structural = load("structural", ROOT / "scripts/research-nq-npx-structural-mapping-2006.py")


def resolve_row(row, master_rows):
    forms = []
    for issuer in row.get("issuerVariants", []):
        for form in structural.cleaned_forms(str(issuer)):
            if form and form not in forms:
                forms.append(form)

    attempts = []
    positives = []
    for form in forms:
        query = {
            "ticker": row.get("ticker"),
            "securityId": row.get("securityId"),
            "issuer": form,
            "aggregateWeight": row.get("aggregateWeight"),
            "asOfReportDate": row.get("asOfReportDate"),
        }
        evidence = flat.resolve(query, master_rows)
        attempts.append({
            "issuerForm": form,
            "classification": evidence.get("classification"),
            "seedCik": evidence.get("seedCik"),
            "seedSource": evidence.get("seedSource"),
            "resolutionSource": evidence.get("resolutionSource"),
            "stateCode": evidence.get("stateCode"),
            "evidenceDateFiled": evidence.get("evidenceDateFiled"),
        })
        if evidence.get("classification") in {"US", "NON_US"}:
            positives.append((evidence["classification"], form, evidence))

    classes = sorted({value[0] for value in positives})
    if len(classes) > 1:
        raise RuntimeError(
            f"historical country conflict {row.get('ticker')} {row.get('securityId')} "
            f"{row.get('asOfReportDate')} {classes}"
        )
    if len(classes) == 1:
        classification = classes[0]
        selected = next(value for value in positives if value[0] == classification)
        return {
            **row,
            "classification": classification,
            "countryIdentityFormUsed": selected[1],
            "resolutionEvidence": selected[2],
            "attempts": attempts,
        }
    return {**row, "classification": "UNKNOWN", "attempts": attempts}


def main():
    data = json.loads(SRC.read_text())
    unresolved = data.get("unresolvedIdentityDates", [])
    years = sorted({
        int(row["asOfReportDate"][:4])
        for row in unresolved if row.get("asOfReportDate")
    })
    master_rows, transports = flat.base.load_master(years) if years else ([], [])

    resolved = {}
    audit = []
    for row in unresolved:
        if not row.get("asOfReportDate") or not row.get("issuerVariants"):
            record = {**row, "classification": "UNKNOWN", "attempts": []}
        else:
            record = resolve_row(row, master_rows)
        resolved[(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))] = record
        audit.append(record)
        print("COUNTRY_RESOLVE", json.dumps({
            key: record.get(key)
            for key in [
                "ticker", "securityId", "asOfReportDate", "classification", "countryIdentityFormUsed"
            ]
        }), flush=True)

    snapshots = []
    for snapshot in data["monthSnapshots"]:
        source_filings = []
        counts = {"US": 0, "NON_US": 0, "UNKNOWN": 0}
        weights = {"US": 0.0, "NON_US": 0.0, "UNKNOWN": 0.0}

        for filing in snapshot["sourceFilings"]:
            holdings = []
            report_date = filing.get("reportDate")
            filing_counts = {"US": 0, "NON_US": 0, "UNKNOWN": 0}
            filing_weights = {"US": 0.0, "NON_US": 0.0, "UNKNOWN": 0.0}

            for holding in filing.get("holdings", []):
                row = dict(holding)
                classification = row.get("countryClassification", "UNKNOWN")
                if classification == "UNKNOWN" and row.get("mappingStatus") == "MATCHED_UNIQUE":
                    evidence = resolved.get((
                        row.get("mappedTicker"),
                        row.get("mappedSecurityId"),
                        report_date,
                    ))
                    if evidence and evidence.get("classification") in {"US", "NON_US"}:
                        classification = evidence["classification"]
                        row["countryClassification"] = classification
                        row["countryReason"] = "PIT_SUBMISSION_HEADER_EXACT_IDENTITY"
                        row["countryResolutionEvidence"] = evidence

                weight = float(row.get("weight") or 0.0)
                filing_counts[classification] += 1
                filing_weights[classification] += weight
                counts[classification] += 1
                weights[classification] += weight
                holdings.append(row)

            source_filings.append({
                **{
                    key: value for key, value in filing.items()
                    if key not in {"holdings", "countryClassificationCounts", "countryClassificationWeights"}
                },
                "countryClassificationCounts": filing_counts,
                "countryClassificationWeights": filing_weights,
                "holdings": holdings,
            })

        snapshots.append({
            **{
                key: value for key, value in snapshot.items()
                if key not in {"sourceFilings", "countryClassificationCounts", "countryClassificationWeights"}
            },
            "countryClassificationCounts": counts,
            "countryClassificationWeights": weights,
            "sourceFilings": source_filings,
        })

    output = {
        "purpose": (
            "Second-stage hybrid H1 2006 country resolution for only previously UNKNOWN deterministically "
            "mapped identities. Uses the validated historical SEC master-index exact issuer-form to unique "
            "CIK resolver and matching complete-submission COMPANY DATA / STATE OF INCORPORATION evidence, "
            "bounded by each holding report date. Accepted structural cleaned issuer forms are reused; no "
            "fuzzy matching, US default, modern state/country, ranks, returns, or strategy outcomes."
        ),
        "masterYears": years,
        "masterIndexTransports": transports,
        "unresolvedInputCount": len(unresolved),
        "resolvedUSCount": sum(row.get("classification") == "US" for row in audit),
        "resolvedNonUSCount": sum(row.get("classification") == "NON_US" for row in audit),
        "remainingUnknownCount": sum(row.get("classification") == "UNKNOWN" for row in audit),
        "resolutionAudit": audit,
        "monthSnapshots": snapshots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        key: value for key, value in output.items()
        if key not in {"resolutionAudit", "monthSnapshots", "masterIndexTransports"}
    }), flush=True)
    for snapshot in snapshots:
        print("MONTH_COUNTRY_FINAL", json.dumps({
            "signalMonth": snapshot["signalMonth"],
            "counts": snapshot["countryClassificationCounts"],
            "weights": snapshot["countryClassificationWeights"],
        }), flush=True)


if __name__ == "__main__":
    main()
