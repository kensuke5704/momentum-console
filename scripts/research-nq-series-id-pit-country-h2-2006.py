#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"

H2_SOURCE_SHA256 = "f79f8d9e6d7fe45cb115a9c7f087dcca00622ff602cc0147e70e860f3528417d"
H2_SOURCE_ARTIFACT_ID = 10038284691
H2_MAPPING_RUN_ID = 34180122700
H2_MAPPING_ARTIFACT_ID = 10038597826
H1_COUNTRY_RUN_ID = 34104858455
H1_COUNTRY_ARTIFACT_ID = 10012280475
BASE_COUNTRY_ARTIFACT_ID = 9944538015
STRUCTURAL_COUNTRY_ARTIFACT_ID = 9944797581

MAPPING = DATA / "nq-series-id-structural-mapping-h2-2006.json"
NPX = DATA / "npx-security-master-2006.json"
BASE = DATA / "sec-submission-header-country-full-merged-2006.json"
STRUCT = DATA / "structural-new-matches-submission-header-country-2006.json"
SHARDS = DATA / "series-id-country-h2-shards"
COUNTRY_OUT = DATA / "nq-series-id-country-pit-h2-2006.json"
DIAGNOSTIC_OUT = DATA / "nq-series-id-country-extension-diagnostic-h2-2006.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def configure(module) -> None:
    module.MAPPING = MAPPING
    module.NPX = NPX
    module.BASE = BASE
    module.STRUCT = STRUCT
    module.SHARDS = SHARDS
    module.COUNTRY_OUT = COUNTRY_OUT
    module.GATE_OUT = DIAGNOSTIC_OUT
    module.CATALOG_SHA = H2_SOURCE_SHA256


def attach_lineage(path: Path, *, diagnostic: bool) -> None:
    payload = json.loads(path.read_text())
    payload["purpose"] = (
        "H2 2006 period-extension country sensitivity diagnostic produced by the frozen H1 strict PIT country implementation. "
        "This is not a new gate and must not be used to tune source discovery, mapping, country rules, or strategy performance."
        if diagnostic
        else
        "H2 2006 strict point-in-time country resolution for deterministic mapped COMMON_EQUITY holdings. The exact authoritative H1 country implementation is reused with Jul-Dec H2 mapped holdings. Explicit historical country, alphabetic CINS, ADR/GDR/ADS semantics, and dated SEC submission-header evidence are retained exactly; unresolved remains UNKNOWN. No 2007 evidence, current-country backfill, fuzzy mapping, rank, return, or strategy outcome is used."
    )
    payload["sourceCatalogArtifactId"] = H2_SOURCE_ARTIFACT_ID
    payload["sourceCatalogSha256"] = H2_SOURCE_SHA256
    payload["mappingRunId"] = H2_MAPPING_RUN_ID
    payload["mappingArtifactId"] = H2_MAPPING_ARTIFACT_ID
    payload["authoritativeH1CountryRunId"] = H1_COUNTRY_RUN_ID
    payload["authoritativeH1CountryArtifactId"] = H1_COUNTRY_ARTIFACT_ID
    payload["baseCountryEvidenceArtifactId"] = BASE_COUNTRY_ARTIFACT_ID
    payload["structuralCountryEvidenceArtifactId"] = STRUCTURAL_COUNTRY_ARTIFACT_ID
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("resolve-shard", "merge"), required=True)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=8)
    args = parser.parse_args()

    module = load_module(
        "authoritative_h1_strict_pit_country",
        ROOT / "scripts/research-nq-hybrid-pit-country-gate-b-h1-2006.py",
    )
    configure(module)

    if args.mode == "resolve-shard":
        module.resolve_shard(args)
        return

    module.merge()
    attach_lineage(COUNTRY_OUT, diagnostic=False)
    attach_lineage(DIAGNOSTIC_OUT, diagnostic=True)

    country = json.loads(COUNTRY_OUT.read_text())
    print("H2_COUNTRY_SUMMARY", json.dumps({
        "sourceCatalogSha256": country.get("catalogSha256"),
        "mappingArtifactId": H2_MAPPING_ARTIFACT_ID,
        "reasonCounts": country.get("reasonCounts"),
        "monthly": [
            {
                "signalMonth": snapshot["signalMonth"],
                "sourceSeriesCount": snapshot["sourceSeriesCount"],
                "mappedCommonEquityCountryCounts": snapshot.get("mappedCommonEquityCountryCounts"),
                "mappedCommonEquityCountryWeights": snapshot.get("mappedCommonEquityCountryWeights"),
                "corpPositiveNonCorpNameCount": snapshot.get("corpPositiveNonCorpNameCount"),
            }
            for snapshot in country.get("monthSnapshots", [])
        ],
    }), flush=True)


if __name__ == "__main__":
    main()
