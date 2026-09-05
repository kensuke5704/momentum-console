#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/research/nq-hybrid-country-resolved-h1-2006.json"
OUT = ROOT / "data/research/nq-hybrid-universe-h1-2006.json"
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


def age_days(as_of, filing_date):
    return max(0, (date.fromisoformat(as_of) - date.fromisoformat(filing_date)).days)


def confirmed_us_holdings(filing):
    holdings = [
        holding for holding in filing.get("holdings", [])
        if holding.get("mappingStatus") == "MATCHED_UNIQUE"
        and holding.get("countryClassification") == "US"
        and float(holding.get("weight") or 0.0) > 0
        and holding.get("mappedTicker")
    ]
    return sorted(holdings, key=lambda holding: float(holding.get("weight") or 0.0), reverse=True)


def source_eligibility(filing):
    name = filing.get("seriesName") or ""
    if STRUCTURED_OR_INCOME.search(name):
        return False, "STRUCTURED_OR_INCOME_NAME"
    if BROAD_BENCHMARK.search(name):
        return False, "BROAD_BENCHMARK_NAME"

    holdings = confirmed_us_holdings(filing)
    if len(holdings) < 10 or len(holdings) > 120:
        return False, "US_HOLDING_COUNT"
    total = sum(float(holding.get("weight") or 0.0) for holding in holdings)
    top_ten = sum(float(holding.get("weight") or 0.0) for holding in holdings[:10])
    if total < 50:
        return False, "US_TOTAL_WEIGHT"
    if top_ten < 25:
        return False, "US_TOP10_WEIGHT"
    return True, "ELIGIBLE"


def main():
    data = json.loads(SRC.read_text())
    snapshots = []

    for snapshot in data["monthSnapshots"]:
        rows = {}
        filing_audit = []

        for filing in snapshot["sourceFilings"]:
            eligible, reason = source_eligibility(filing)
            holdings = confirmed_us_holdings(filing)
            total = sum(float(holding.get("weight") or 0.0) for holding in holdings)
            top_ten = sum(float(holding.get("weight") or 0.0) for holding in holdings[:10])
            filing_audit.append({
                "canonicalIdentity": filing.get("canonicalIdentity"),
                "identityRegime": filing.get("identityRegime"),
                "seriesId": filing.get("seriesId"),
                "legacyIdentity": filing.get("legacyIdentity"),
                "seriesName": filing.get("seriesName"),
                "filingDate": filing.get("filingDate"),
                "eligible": eligible,
                "eligibilityReason": reason,
                "usHoldingCount": len(holdings),
                "usTotalWeight": total,
                "usTop10Weight": top_ten,
            })
            if not eligible:
                continue

            recency_factor = math.exp(-age_days(snapshot["asOf"], filing["filingDate"]) / 120)
            source_identity = (
                filing.get("canonicalIdentity")
                or filing.get("seriesId")
                or filing.get("legacyIdentity")
            )
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
            score = (
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
                "universeScore": score,
            })

        members.sort(key=lambda row: (
            -row["universeScore"],
            -row["etfCount"],
            -row["aggregateWeight"],
            row["symbol"],
        ))
        members = [
            {**row, "universeRank": index + 1}
            for index, row in enumerate(members[:80])
        ]
        snapshots.append({
            "signalMonth": snapshot["signalMonth"],
            "asOf": snapshot["asOf"],
            "sourceSeriesCount": len(snapshot["sourceFilings"]),
            "eligibleSourceSeriesCount": sum(row["eligible"] for row in filing_audit),
            "sourceEligibilityAudit": filing_audit,
            "symbols": members,
        })
        print("MONTH_UNIVERSE", json.dumps({
            "signalMonth": snapshot["signalMonth"],
            "sourceSeriesCount": len(snapshot["sourceFilings"]),
            "eligibleSourceSeriesCount": sum(row["eligible"] for row in filing_audit),
            "universeSize": len(members),
            "symbols": [row["symbol"] for row in members],
        }), flush=True)

    output = {
        "purpose": (
            "Conservative H1 2006 historical Universe reconstruction using the exact Production source-name "
            "exclusions, 10-120 confirmed-US deterministically mapped holdings, at least 50 confirmed-US "
            "total weight and at least 25 top-10 weight, followed by the Production breadth filter, recency "
            "score, ordering and Top80. UNKNOWN/unmapped holdings do not count as US. No result is used to "
            "tune source, mapping, country, eligibility or ranking rules."
        ),
        "sourceEligibilityRule": (
            "Production isEligibleEtf semantics applied only after COMMON_EQUITY + deterministic mapping + "
            "conservative country filtering"
        ),
        "breadthScoreRule": (
            "etfCount>=2 OR maxWeight>=4; score=3*log1p(etfCount)+0.5*log1p(aggregateWeight)+"
            "0.5*log1p(recencyWeight); Top80"
        ),
        "monthSnapshots": snapshots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
