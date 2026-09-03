#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/sec-nport/bootstrap.json.gz"
OUT = ROOT / "data/research/nport-corp-redundancy.json"


def pick(obj: dict, *keys):
    for k in keys:
        if k in obj and obj[k] not in (None, ""):
            return obj[k]
    return None


def main() -> None:
    with gzip.open(SRC, "rt", encoding="utf-8") as f:
        data = json.load(f)

    filings = data.get("filings", data if isinstance(data, list) else [])
    total_holdings = 0
    ec_us = 0
    ec_us_corp = 0
    issuer_types = Counter()
    by_month = defaultdict(lambda: {"ecUs": 0, "corp": 0, "types": Counter()})
    examples = defaultdict(list)

    for filing in filings:
        report = str(pick(filing, "reportDate", "report_date") or "")
        month = report[:7] if len(report) >= 7 else "UNKNOWN"
        holdings = filing.get("holdings") or []
        for h in holdings:
            total_holdings += 1
            asset = str(pick(h, "assetCategory", "assetCat", "asset_category", "ASSET_CAT") or "").upper()
            country = str(pick(h, "investmentCountry", "country", "investment_country", "INVESTMENT_COUNTRY") or "").upper()
            issuer = str(pick(h, "issuerType", "issuer_type", "ISSUER_TYPE") or "").upper()
            if asset == "EC" and country == "US":
                ec_us += 1
                issuer_types[issuer or "MISSING"] += 1
                by_month[month]["ecUs"] += 1
                by_month[month]["types"][issuer or "MISSING"] += 1
                if issuer == "CORP":
                    ec_us_corp += 1
                    by_month[month]["corp"] += 1
                elif len(examples[issuer or "MISSING"]) < 12:
                    examples[issuer or "MISSING"].append({
                        "name": pick(h, "name", "issuerName", "issuer_name"),
                        "ticker": pick(h, "ticker", "symbol"),
                        "asset": asset,
                        "country": country,
                        "issuerType": issuer or "MISSING",
                        "reportDate": report,
                    })

    month_rows = []
    for month in sorted(by_month):
        row = by_month[month]
        month_rows.append({
            "month": month,
            "ecUs": row["ecUs"],
            "corp": row["corp"],
            "corpShare": row["corp"] / row["ecUs"] if row["ecUs"] else None,
            "issuerTypes": dict(row["types"]),
        })

    out = {
        "purpose": "Structural diagnostic of whether N-PORT ISSUER_TYPE=CORP adds material filtering after ASSET_CAT=EC and INVESTMENT_COUNTRY=US. No returns or strategy outcomes used.",
        "source": "data/sec-nport/bootstrap.json.gz",
        "totalFilings": len(filings),
        "totalHoldings": total_holdings,
        "ecUsHoldings": ec_us,
        "ecUsCorpHoldings": ec_us_corp,
        "corpShareWithinEcUs": ec_us_corp / ec_us if ec_us else None,
        "issuerTypeWithinEcUs": dict(issuer_types),
        "nonCorpExamples": dict(examples),
        "byReportMonth": month_rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k not in {"nonCorpExamples", "byReportMonth"}}), flush=True)
    for typ, rows in examples.items():
        print("NON_CORP", typ, json.dumps(rows[:5]), flush=True)


if __name__ == "__main__":
    main()
