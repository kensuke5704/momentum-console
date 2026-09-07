#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date
from pathlib import Path

STRUCTURED_OR_INCOME = re.compile(
    r"\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|"
    r"buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b",
    re.I,
)
BROAD_BENCHMARK = re.compile(
    r"\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|"
    r"dow jones|large cap blend|mid cap blend|small cap blend)\b",
    re.I,
)
NON_CORP_POSITIVE_NAME = [
    re.compile(r"\b(?:ETF|EXCHANGE[ -]TRADED|MUTUAL FUND|INDEX FUND|INVESTMENT FUND|INCOME FUND|EQUITY FUND|MONEY MARKET FUND)\b", re.I),
    re.compile(r"\b(?:HEDGE FUND|PRIVATE EQUITY FUND|VENTURE FUND)\b", re.I),
    re.compile(r"\b(?:UNITED STATES TREASURY|U\.S\. TREASURY|GOVERNMENT OF|REPUBLIC OF|KINGDOM OF)\b", re.I),
    re.compile(r"\b(?:CITY OF|COUNTY OF|MUNICIPAL)\b", re.I),
]


def positive_non_corp_name(description: str | None) -> bool:
    text = str(description or "")
    return any(pattern.search(text) for pattern in NON_CORP_POSITIVE_NAME)


def filtered_primary_holdings(filing: dict) -> list[dict]:
    out = []
    for holding in filing.get("holdings", []):
        if holding.get("legacyAssetSection") != "COMMON_EQUITY":
            continue
        if holding.get("mappingStatus") != "MATCHED_UNIQUE":
            continue
        if holding.get("countryClassification") != "US":
            continue
        if positive_non_corp_name(holding.get("description")):
            continue
        if float(holding.get("weight") or 0.0) <= 0:
            continue
        if not holding.get("mappedTicker"):
            continue
        out.append(holding)
    return sorted(out, key=lambda row: float(row.get("weight") or 0.0), reverse=True)


def source_eligibility(filing: dict) -> tuple[bool, str, list[dict]]:
    name = filing.get("seriesName") or ""
    if STRUCTURED_OR_INCOME.search(name):
        return False, "STRUCTURED_OR_INCOME", []
    if BROAD_BENCHMARK.search(name):
        return False, "BROAD_BENCHMARK", []
    holdings = filtered_primary_holdings(filing)
    if not 10 <= len(holdings) <= 120:
        return False, "HOLDING_COUNT", holdings
    total_weight = sum(float(row.get("weight") or 0.0) for row in holdings)
    top10_weight = sum(float(row.get("weight") or 0.0) for row in holdings[:10])
    if total_weight < 50:
        return False, "TOTAL_WEIGHT", holdings
    if top10_weight < 25:
        return False, "TOP10_WEIGHT", holdings
    return True, "ELIGIBLE", holdings


def build_snapshot(snapshot: dict) -> dict:
    rows: dict[str, dict] = {}
    source_audit = []
    as_of = date.fromisoformat(snapshot["asOf"])

    for filing in snapshot.get("sourceFilings", []):
        eligible, reason, holdings = source_eligibility(filing)
        source_audit.append({
            "canonicalIdentity": filing.get("canonicalIdentity"),
            "seriesId": filing.get("seriesId"),
            "legacyIdentity": filing.get("legacyIdentity"),
            "seriesName": filing.get("seriesName"),
            "filingDate": filing.get("filingDate"),
            "eligible": eligible,
            "eligibilityReason": reason,
            "filteredHoldingCount": len(holdings),
            "filteredTotalWeight": sum(float(row.get("weight") or 0.0) for row in holdings),
            "filteredTop10Weight": sum(float(row.get("weight") or 0.0) for row in holdings[:10]),
        })
        if not eligible:
            continue

        filing_date = date.fromisoformat(filing["filingDate"])
        age_days = max(0, (as_of - filing_date).days)
        recency_factor = math.exp(-age_days / 120)
        source_identity = filing.get("canonicalIdentity") or filing.get("seriesId") or filing.get("legacyIdentity")
        if not source_identity:
            raise RuntimeError(f"missing source identity: {filing.get('seriesName')}")

        for holding in holdings:
            symbol = holding["mappedTicker"].strip().upper()
            weight = float(holding.get("weight") or 0.0)
            row = rows.setdefault(symbol, {
                "seriesIds": set(),
                "aggregateWeight": 0.0,
                "maxWeight": 0.0,
                "recencyWeight": 0.0,
            })
            row["seriesIds"].add(source_identity)
            row["aggregateWeight"] += weight
            row["maxWeight"] = max(row["maxWeight"], weight)
            row["recencyWeight"] += weight * recency_factor

    members = []
    for symbol, row in rows.items():
        etf_count = len(row["seriesIds"])
        if not (etf_count >= 2 or row["maxWeight"] >= 4):
            continue
        universe_score = (
            3 * math.log1p(etf_count)
            + 0.5 * math.log1p(row["aggregateWeight"])
            + 0.5 * math.log1p(row["recencyWeight"])
        )
        members.append({
            "symbol": symbol,
            "etfCount": etf_count,
            "aggregateWeight": row["aggregateWeight"],
            "maxWeight": row["maxWeight"],
            "recencyWeight": row["recencyWeight"],
            "universeScore": universe_score,
        })

    members.sort(key=lambda row: (
        -row["universeScore"],
        -row["etfCount"],
        -row["aggregateWeight"],
        row["symbol"],
    ))
    members = [{**row, "universeRank": i + 1} for i, row in enumerate(members[:80])]

    return {
        "signalMonth": snapshot["signalMonth"],
        "asOf": snapshot["asOf"],
        "sourceSeriesCount": len(snapshot.get("sourceFilings", [])),
        "eligibleSourceSeriesCount": sum(bool(row["eligible"]) for row in source_audit),
        "sourceEligibilityAudit": source_audit,
        "symbols": members,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-catalog-sha")
    args = parser.parse_args()

    source = json.loads(Path(args.input).read_text())
    catalog_sha = source.get("catalogSha256")
    if args.expected_catalog_sha and catalog_sha != args.expected_catalog_sha:
        raise RuntimeError(f"catalog SHA mismatch: {catalog_sha}")

    snapshots = [build_snapshot(snapshot) for snapshot in source.get("monthSnapshots", [])]
    output = {
        "purpose": "Frozen historical Universe builder core after Gate B PASS. Applies COMMON_EQUITY -> conservative PIT US -> CORP positive-exclusion bridge -> Production source eligibility -> Production breadth score -> Top80. It performs no source discovery, identity repair, country inference, fuzzy mapping, or strategy-performance tuning.",
        "catalogSha256": catalog_sha,
        "eligibilityOrder": "COMMON_EQUITY -> US -> CORP -> source eligibility",
        "sourceEligibility": "name exclusions; 10-120 retained holdings; retained total weight >=50; retained top10 weight >=25",
        "breadthRule": "etfCount>=2 OR maxWeight>=4; score=3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight); Top80",
        "monthSnapshots": snapshots,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    for snapshot in snapshots:
        print("HISTORICAL_UNIVERSE", json.dumps({
            "signalMonth": snapshot["signalMonth"],
            "eligibleSourceSeriesCount": snapshot["eligibleSourceSeriesCount"],
            "universeSize": len(snapshot["symbols"]),
            "top2": [row["symbol"] for row in snapshot["symbols"][:2]],
        }), flush=True)


if __name__ == "__main__":
    main()
