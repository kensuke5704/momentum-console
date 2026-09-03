#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIT = ROOT / "data/research/nq-pit-holdings-2006-corrected.json"
OUT = ROOT / "data/research/nq-pit-holdings-2006-ec-filtered.json"

espec = importlib.util.spec_from_file_location("ec", ROOT / "scripts" / "research-nq-per-holding-ec-2006.py")
ec = importlib.util.module_from_spec(espec)
espec.loader.exec_module(ec)

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts" / "research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)


def main() -> None:
    pit = json.loads(PIT.read_text())
    source_cache = {}
    records = []
    rejected = []

    for record in pit["records"]:
        filename = record["sourceFilename"]
        if filename not in source_cache:
            _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(filename))
            series = seg.meta.parse_series_contracts(submission, record["registrant"])
            etf = [s for s in series if s["isEtf"]]
            _, text = seg.embedded_primary_nq(submission)
            grouped, _ = seg.grouped_schedule_blocks(text, etf)
            source_cache[filename] = grouped
        grouped = source_cache[filename]
        vis = seg.visible("\n".join(grouped.get(record["seriesId"], [])))

        annotated = []
        for h in record["holdings"]:
            section, alias = ec.locate_section(vis, h["description"])
            annotated.append({**h, "legacyAssetSection": section, "matchedSourceAlias": alias})

        common = [h for h in annotated if h["legacyAssetSection"] == "COMMON_EQUITY"]
        unknown = [h for h in annotated if h["legacyAssetSection"] == "UNKNOWN"]
        excluded = [h for h in annotated if h["legacyAssetSection"] not in {"COMMON_EQUITY", "UNKNOWN"}]
        common.sort(key=lambda h: float(h.get("weight") or 0), reverse=True)
        total_common = sum(float(h.get("weight") or 0) for h in common)
        top10_common = sum(float(h.get("weight") or 0) for h in common[:10])

        # Preserve the original parser-relative portfolio weights. Do not renormalize
        # after EC filtering: this retains the share of the portfolio that is common
        # equity and is closer to N-PORT percentage-of-net-assets semantics.
        structurally_usable = bool(
            record.get("eligibleByName")
            and 10 <= len(common) <= 120
            and total_common >= 50.0
            and top10_common >= 25.0
        )
        summary = {
            "seriesId": record["seriesId"],
            "seriesName": record["seriesName"],
            "fundTickers": record.get("fundTickers", []),
            "originalHoldingCount": len(annotated),
            "commonEquityCount": len(common),
            "commonEquityWeight": total_common,
            "top10CommonEquityWeight": top10_common,
            "unknownCount": len(unknown),
            "excludedNonEcCount": len(excluded),
            "structurallyUsableAfterEc": structurally_usable,
        }
        print("SERIES", json.dumps(summary), flush=True)

        if not structurally_usable:
            rejected.append(summary)
            continue

        records.append({
            **{k: v for k, v in record.items() if k != "holdings"},
            "assetCategoryBridge": "EXPLICIT_NQ_COMMON_EQUITY_SECTION",
            "weightRuleAfterEc": "Original parser-relative portfolio weights preserved; no post-EC renormalization.",
            "top10Weight": top10_common,
            "parsedMarketValueTotal": record.get("parsedMarketValueTotal"),
            "structurallyUsable": True,
            "holdings": [
                {k: v for k, v in h.items() if k != "matchedSourceAlias"}
                for h in common
            ],
        })

    out = {
        "year": 2006,
        "purpose": "Corrected N-Q PIT holdings after applying the explicit per-holding COMMON_EQUITY section bridge as a legacy ASSET_CAT=EC analogue. No US/CORP filtering and no returns/performance data used.",
        "sourceArtifact": "9878011119",
        "ecRule": "Retain only holdings that inherit an explicit COMMON STOCK(S/SHARES) schedule section. SHORT_TERM, DEBT, PREFERRED and UNKNOWN are not included. Unknown is never coerced to EC.",
        "weightRule": "Preserve original parser-relative portfolio weights after filtering; do not renormalize common equities to 100.",
        "eligibilityRule": "Production-style name exclusion plus 10-120 EC holdings, total EC weight >=50, and top-10 EC weight >=25.",
        "pitSeriesRecords": len(records),
        "rejectedSeries": rejected,
        "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({"pitSeriesRecords": len(records), "rejectedSeries": len(rejected)}), flush=True)


if __name__ == "__main__":
    main()
