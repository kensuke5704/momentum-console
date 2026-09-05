#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "data/research/nq-hybrid-structural-mapping-h1-2006.json"
NPX = ROOT / "data/research/npx-security-master-2006.json"
BASE = ROOT / "data/research/sec-submission-header-country-full-merged-2006.json"
STRUCT = ROOT / "data/research/structural-new-matches-submission-header-country-2006.json"
OUT = ROOT / "data/research/nq-hybrid-country-cache-h1-2006.json"
RECEIPT = re.compile(
    r"\b(?:ADR|GDR|ADS|AMERICAN\s+DEPOSITARY|GLOBAL\s+DEPOSITARY|DEPOSITARY\s+RECEIPT)S?\b",
    re.I,
)


def identity_key(ticker, security_id):
    return ((ticker or "").upper(), security_id or None)


def is_non_us_cins(security_id):
    value = (security_id or "").strip().upper()
    return len(value) == 9 and value[0].isalpha() and value[0] != "U"


def main():
    mapping = json.loads(MAPPING.read_text())
    npx = json.loads(NPX.read_text())
    base = json.loads(BASE.read_text())
    structural = json.loads(STRUCT.read_text())

    evidence = defaultdict(list)
    for source, rows in (
        ("BASELINE_SUBMISSION_HEADER", base.get("identityRows", [])),
        ("STRUCTURAL_SUBMISSION_HEADER", structural.get("rows", [])),
    ):
        for row in rows:
            classification = row.get("classification")
            if classification not in {"US", "NON_US"}:
                continue
            evidence[identity_key(row.get("ticker"), row.get("securityId"))].append({
                "classification": classification,
                "source": source,
                "asOfReportDate": row.get("asOfReportDate"),
                "resolutionSource": row.get("resolutionSource"),
                "evidenceDateFiled": row.get("evidenceDateFiled"),
                "stateCode": row.get("stateCode"),
            })

    issuers = defaultdict(set)
    for row in npx.get("records", []):
        ticker, security_id = row.get("ticker"), row.get("securityId")
        if ticker:
            issuer = row.get("issuer") or row.get("normalizedIssuer") or ""
            if issuer:
                issuers[identity_key(ticker, security_id)].add(issuer)

    unresolved = defaultdict(lambda: {
        "aggregateWeight": 0.0,
        "occurrenceCount": 0,
        "issuerVariants": set(),
    })
    snapshots = []
    reason_counts = Counter()

    for snapshot in mapping["monthSnapshots"]:
        source_filings = []
        month_counts = Counter()
        month_weights = defaultdict(float)

        for filing in snapshot["sourceFilings"]:
            holdings = []
            filing_counts = Counter()
            filing_weights = defaultdict(float)
            report_date = filing.get("reportDate")

            for holding in filing.get("holdings", []):
                weight = float(holding.get("weight") or 0.0)
                classification = "UNKNOWN"
                reason = "UNRESOLVED"
                positive_evidence = []

                if holding.get("mappingStatus") == "MATCHED_UNIQUE":
                    key = identity_key(holding.get("mappedTicker"), holding.get("mappedSecurityId"))
                    current_report = report_date or holding.get("reportDate")
                    usable = [
                        row for row in evidence.get(key, [])
                        if not row.get("asOfReportDate")
                        or (current_report and row["asOfReportDate"] <= current_report)
                    ]
                    cache_classes = sorted({row["classification"] for row in usable})
                    if len(cache_classes) > 1:
                        raise RuntimeError(
                            f"country cache conflict {key} report={current_report} classes={cache_classes}"
                        )

                    explicit = (
                        holding.get("legacyCountryClassification")
                        if holding.get("legacyCountryClassification") in {"US", "NON_US"}
                        else None
                    )
                    cins_non_us = is_non_us_cins(holding.get("mappedSecurityId"))
                    receipt_non_us = bool(RECEIPT.search(str(holding.get("description") or "")))
                    structural_non_us = cins_non_us or receipt_non_us

                    if explicit and structural_non_us and explicit != "NON_US":
                        raise RuntimeError(
                            f"explicit N-Q/CINS-receipt conflict {key} report={current_report} explicit={explicit}"
                        )
                    if explicit and cache_classes and explicit != cache_classes[0]:
                        raise RuntimeError(
                            f"explicit N-Q/cache conflict {key} report={current_report} "
                            f"explicit={explicit} cache={cache_classes[0]}"
                        )
                    if structural_non_us and cache_classes and cache_classes[0] != "NON_US":
                        raise RuntimeError(
                            f"CINS-receipt/cache conflict {key} report={current_report} cache={cache_classes[0]}"
                        )

                    if explicit:
                        classification = explicit
                        reason = "NQ_EXPLICIT_COUNTRY_SECTION"
                    elif cins_non_us:
                        classification = "NON_US"
                        reason = "NON_US_CINS"
                    elif receipt_non_us:
                        classification = "NON_US"
                        reason = "EXPLICIT_DEPOSITARY_RECEIPT"
                    elif cache_classes:
                        classification = cache_classes[0]
                        reason = "FROZEN_POSITIVE_IDENTITY_EVIDENCE"
                        positive_evidence = usable

                    if classification == "UNKNOWN":
                        row = unresolved[(key[0], key[1], current_report)]
                        row["aggregateWeight"] += weight
                        row["occurrenceCount"] += 1
                        row["issuerVariants"].update(issuers.get(key, set()))

                output = {
                    **holding,
                    "countryClassification": classification,
                    "countryReason": reason,
                }
                if positive_evidence:
                    output["countryEvidence"] = positive_evidence
                holdings.append(output)
                filing_counts[classification] += 1
                filing_weights[classification] += weight
                month_counts[classification] += 1
                month_weights[classification] += weight
                reason_counts[reason] += 1

            source_filings.append({
                **{key: value for key, value in filing.items() if key != "holdings"},
                "countryClassificationCounts": dict(filing_counts),
                "countryClassificationWeights": dict(filing_weights),
                "holdings": holdings,
            })

        snapshots.append({
            **{key: value for key, value in snapshot.items() if key != "sourceFilings"},
            "countryClassificationCounts": dict(month_counts),
            "countryClassificationWeights": dict(month_weights),
            "sourceFilings": source_filings,
        })

    unresolved_rows = []
    for (ticker, security_id, report_date), row in sorted(unresolved.items()):
        unresolved_rows.append({
            "ticker": ticker,
            "securityId": security_id,
            "asOfReportDate": report_date,
            "aggregateWeight": row["aggregateWeight"],
            "occurrenceCount": row["occurrenceCount"],
            "issuerVariants": sorted(row["issuerVariants"]),
        })

    output = {
        "purpose": (
            "First-stage hybrid H1 2006 country classification. Highest priority is explicit country "
            "section evidence in the same historical N-Q schedule. Next are deterministic non-US CINS "
            "and depositary-receipt rules. Previously established positive historical identity-country "
            "evidence is reused only when its as-of report date is no later than the current holding "
            "report date. No US default, fuzzy matching, modern country default, ranks, returns, or "
            "strategy outcomes are used. Remaining identities stay UNKNOWN for a separate historical "
            "SEC-header resolver."
        ),
        "countryEvidenceRule": (
            "N-Q explicit country section -> non-US CINS/explicit depositary receipt -> "
            "PIT-safe positive historical identity cache -> UNKNOWN"
        ),
        "positiveEvidenceIdentityCount": len(evidence),
        "reasonCounts": dict(reason_counts),
        "unresolvedIdentityDateCount": len(unresolved_rows),
        "unresolvedIdentityDates": unresolved_rows,
        "monthSnapshots": snapshots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        key: value for key, value in output.items()
        if key not in {"unresolvedIdentityDates", "monthSnapshots"}
    }), flush=True)
    for snapshot in snapshots:
        print("MONTH_COUNTRY_CACHE", json.dumps({
            "signalMonth": snapshot["signalMonth"],
            "counts": snapshot["countryClassificationCounts"],
            "weights": snapshot["countryClassificationWeights"],
        }), flush=True)


if __name__ == "__main__":
    main()
