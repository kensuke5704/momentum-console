#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID_CATALOG = Path(os.environ.get("ID_CATALOG_PATH", str(ROOT / "data/research/sec-historical-etf-series-source-catalog-complete-h1-2006.json")))
LEGACY = Path(os.environ.get("LEGACY_CATALOG_PATH", str(ROOT / "data/research/sec-legacy-etf-series-source-q4-2005.json")))
OUT = ROOT / "data/research/sec-hybrid-etf-source-catalog-h1-2006.json"


def norm(value: str) -> str:
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", html.unescape(value or "").upper()).split())


def main() -> None:
    ids = json.loads(ID_CATALOG.read_text())
    legacy = json.loads(LEGACY.read_text())
    id_by_cik_name = defaultdict(list)
    for row in ids["positiveSeries"]:
        id_by_cik_name[(row["cik"], norm(row["seriesName"]))].append(row)

    month_snapshots = []
    bridge_audit = []
    for id_snap in ids["monthSnapshots"]:
        asof = id_snap["asOf"]
        by_identity = {}
        for row in id_snap["sourceFilings"]:
            source = {
                **row,
                "sourceIdentity": row["seriesId"],
                "identityRegime": "SEC_SERIES_ID",
                "sourceInventoryPeriod": row.get("inventoryPeriod", "2006H1"),
            }
            by_identity[source["sourceIdentity"]] = source

        month_bridge = []
        unbridged = []
        for row in legacy["legacySeries"]:
            if row["sourceFilingDate"] > asof or row["evidenceDateFiled"] > asof:
                continue
            candidates = [
                x for x in id_by_cik_name.get((row["cik"], row["normalizedSeriesName"]), [])
                if x["evidenceDateFiled"] <= asof
            ]
            if len(candidates) == 1:
                identity = candidates[0]["seriesId"]
                bridge_rule = "SAME_CIK_EXACT_NORMALIZED_NAME_UNIQUE_PUBLIC_ID"
            else:
                identity = row["legacyIdentity"]
                bridge_rule = "UNBRIDGED_LEGACY_IDENTITY"
                unbridged.append(row)
            candidate_source = {
                "sourceIdentity": identity,
                "seriesId": identity,
                "seriesName": row["seriesName"],
                "accession": row["sourceAccession"],
                "cik": row["cik"],
                "registrant": row["registrant"],
                "filingDate": row["sourceFilingDate"],
                "evidenceDateFiled": row["evidenceDateFiled"],
                "evidenceForm": row["evidenceForm"],
                "evidenceFilename": row["evidenceFilename"],
                "binding": row["binding"],
                "identityRegime": "PRE_SERIES_ID_EXPLICIT_TITLE",
                "sourceInventoryPeriod": "2005Q4",
                "legacyIdentity": row["legacyIdentity"],
                "legacyNormalizedSeriesName": row["normalizedSeriesName"],
                "legacyToSeriesIdBridgeRule": bridge_rule,
            }
            current = by_identity.get(identity)
            if current is None or (candidate_source["filingDate"], candidate_source["accession"]) > (current["filingDate"], current["accession"]):
                by_identity[identity] = candidate_source
            month_bridge.append({
                "legacyIdentity": row["legacyIdentity"],
                "legacySeriesName": row["seriesName"],
                "canonicalIdentity": identity,
                "rule": bridge_rule,
                "publicIdCandidateCount": len(candidates),
            })

        sources = sorted(by_identity.values(), key=lambda x: (x["sourceIdentity"], x["filingDate"], x["accession"]))
        unbridged_ciks = Counter(row["cik"] for row in unbridged)
        id_ciks = Counter(row["cik"] for row in id_snap["sourceFilings"])
        overlap_ciks = sorted(cik for cik in unbridged_ciks if id_ciks.get(cik))
        month_snapshots.append({
            "signalMonth": id_snap["signalMonth"],
            "asOf": asof,
            "sourceSeriesCount": len(sources),
            "idEraSourceSeriesCountBeforeMerge": len(id_snap["sourceFilings"]),
            "legacyCandidateSeriesCount": len(month_bridge),
            "legacyExactNameBridgedCount": sum(x["rule"].startswith("SAME_CIK") for x in month_bridge),
            "legacyUnbridgedCount": sum(x["rule"] == "UNBRIDGED_LEGACY_IDENTITY" for x in month_bridge),
            "unbridgedLegacyCiksAlsoHavingIdSources": overlap_ciks,
            "sourceInventoryPeriodCounts": dict(Counter(row["sourceInventoryPeriod"] for row in sources)),
            "identityRegimeCounts": dict(Counter(row["identityRegime"] for row in sources)),
            "sourceFilings": sources,
        })
        bridge_audit.append({"signalMonth": id_snap["signalMonth"], "rows": month_bridge})

    out = {
        "purpose": (
            "Hybrid H1 2006 ETF source catalog across the SEC Series/Class identifier regime boundary. "
            "Pre-2006-02-06 sources may use contemporaneous explicit N-Q schedule titles validated by issuer-own "
            "operational evidence. A legacy identity is replaced by a public SEC Series ID only when same CIK + "
            "exact normalized Series name resolves uniquely by that month end. No fuzzy rename bridge, holdings "
            "similarity, returns, ranks, or strategy outcomes are used. If a legacy identity remains unbridged while "
            "the same registrant also has ID-era sources, the overlap is exposed for sensitivity analysis rather than "
            "silently merged. For a canonical identity, the latest public N-Q source filing wins."
        ),
        "source": "HYBRID_PRE_SERIES_ID_PLUS_SEC_SERIES_ID_PIT_SOURCE_CATALOG_V1",
        "seriesIdMandatoryDate": "2006-02-06",
        "idCatalogSource": ids.get("source"),
        "legacyCatalogSource": legacy.get("source"),
        "monthSnapshots": month_snapshots,
        "bridgeAudit": bridge_audit,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "source": out["source"],
        "months": [
            {k: snap[k] for k in (
                "signalMonth", "sourceSeriesCount", "idEraSourceSeriesCountBeforeMerge",
                "legacyCandidateSeriesCount", "legacyExactNameBridgedCount", "legacyUnbridgedCount"
            )}
            for snap in month_snapshots
        ],
    }), flush=True)


if __name__ == "__main__":
    main()
