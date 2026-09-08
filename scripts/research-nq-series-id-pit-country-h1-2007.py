#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'

H1_COUNTRY_RUN_ID = 34104858455
H1_COUNTRY_ARTIFACT_ID = 10012280475
BASE_COUNTRY_ARTIFACT_ID = 9944538015
STRUCTURAL_COUNTRY_ARTIFACT_ID = 9944797581
NPX_ARTIFACT_ID = 9876020712

MAPPING = DATA / 'nq-series-id-structural-mapping-h1-2007.json'
NPX = DATA / 'npx-security-master-2006.json'
BASE = DATA / 'sec-submission-header-country-full-merged-2006.json'
STRUCT = DATA / 'structural-new-matches-submission-header-country-2006.json'
SHARDS = DATA / 'series-id-country-h1-2007-shards'
COUNTRY_OUT = DATA / 'nq-series-id-country-pit-h1-2007.json'
DIAGNOSTIC_OUT = DATA / 'nq-series-id-country-extension-diagnostic-h1-2007.json'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def configure(module, source_sha: str) -> None:
    module.MAPPING = MAPPING
    module.NPX = NPX
    module.BASE = BASE
    module.STRUCT = STRUCT
    module.SHARDS = SHARDS
    module.COUNTRY_OUT = COUNTRY_OUT
    module.GATE_OUT = DIAGNOSTIC_OUT
    module.CATALOG_SHA = source_sha

    # Period-only extension of the frozen H1 resolver. The original implementation
    # calls flat.base.load_master([2005, 2006]). Intercept only that loader so 2007
    # SEC master-index rows are available. flat.resolve itself continues to filter
    # issuer rows to dateFiled <= the row signal date, and the frozen resolve_one /
    # merge paths independently hard-fail any positive evidenceDateFiled > signalDate.
    original_loadmod = module.loadmod

    def period_loadmod(name, path):
        loaded = original_loadmod(name, path)
        if name == 'flat':
            original_load_master = loaded.base.load_master

            def load_master_through_2007(years):
                return original_load_master(sorted(set(years) | {2007}))

            loaded.base.load_master = load_master_through_2007
        return loaded

    module.loadmod = period_loadmod


def attach_lineage(path: Path, *, diagnostic: bool, source_artifact_id: int, source_sha: str, mapping_run_id: int, mapping_artifact_id: int) -> None:
    payload = json.loads(path.read_text())
    payload['purpose'] = (
        'H1 2007 period-extension country sensitivity diagnostic produced by the frozen H1 strict PIT country semantics. '
        'The only period extension is SEC master-index coverage through 2007; every accepted filing evidence date remains bounded by the signal date. This diagnostic is not a new gate and must not be used to tune source discovery, mapping, country rules, or strategy performance.'
        if diagnostic
        else
        'H1 2007 strict point-in-time country resolution for deterministic mapped COMMON_EQUITY holdings. The authoritative H1 country implementation is reused with only SEC master-index year coverage extended to include 2007. Explicit historical country, alphabetic CINS, ADR/GDR/ADS semantics, and dated SEC submission-header evidence are retained; unresolved remains UNKNOWN. Every positive filing evidence date must be public by the signal date. No current-country backfill, fuzzy mapping, rank, return, or strategy outcome is used.'
    )
    payload['sourceCatalogArtifactId'] = source_artifact_id
    payload['sourceCatalogSha256'] = source_sha
    payload['mappingRunId'] = mapping_run_id
    payload['mappingArtifactId'] = mapping_artifact_id
    payload['authoritativeH1CountryRunId'] = H1_COUNTRY_RUN_ID
    payload['authoritativeH1CountryArtifactId'] = H1_COUNTRY_ARTIFACT_ID
    payload['baseCountryEvidenceArtifactId'] = BASE_COUNTRY_ARTIFACT_ID
    payload['structuralCountryEvidenceArtifactId'] = STRUCTURAL_COUNTRY_ARTIFACT_ID
    payload['npxArtifactId'] = NPX_ARTIFACT_ID
    payload['periodExtensionMasterYears'] = [2005, 2006, 2007]
    path.write_text(json.dumps(payload, indent=2) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('resolve-shard', 'merge'), required=True)
    parser.add_argument('--shard-index', type=int, default=0)
    parser.add_argument('--shard-count', type=int, default=8)
    args = parser.parse_args()

    source_artifact_id = int(os.environ['SOURCE_CATALOG_ARTIFACT_ID'])
    source_sha = os.environ['SOURCE_CATALOG_SHA256'].strip().lower()
    mapping_run_id = int(os.environ['MAPPING_RUN_ID'])
    mapping_artifact_id = int(os.environ['MAPPING_ARTIFACT_ID'])
    if source_artifact_id <= 0 or mapping_run_id <= 0 or mapping_artifact_id <= 0 or len(source_sha) != 64:
        raise RuntimeError('fixed source/mapping lineage environment is invalid')

    module = load_module(
        'authoritative_h1_strict_pit_country',
        ROOT / 'scripts/research-nq-hybrid-pit-country-gate-b-h1-2006.py',
    )
    configure(module, source_sha)

    if args.mode == 'resolve-shard':
        module.resolve_shard(args)
        return

    module.merge()
    attach_lineage(
        COUNTRY_OUT,
        diagnostic=False,
        source_artifact_id=source_artifact_id,
        source_sha=source_sha,
        mapping_run_id=mapping_run_id,
        mapping_artifact_id=mapping_artifact_id,
    )
    attach_lineage(
        DIAGNOSTIC_OUT,
        diagnostic=True,
        source_artifact_id=source_artifact_id,
        source_sha=source_sha,
        mapping_run_id=mapping_run_id,
        mapping_artifact_id=mapping_artifact_id,
    )

    country = json.loads(COUNTRY_OUT.read_text())
    print('H1_2007_COUNTRY_SUMMARY', json.dumps({
        'sourceCatalogSha256': country.get('catalogSha256'),
        'mappingArtifactId': mapping_artifact_id,
        'reasonCounts': country.get('reasonCounts'),
        'monthly': [
            {
                'signalMonth': snapshot['signalMonth'],
                'sourceSeriesCount': snapshot['sourceSeriesCount'],
                'mappedCommonEquityCountryCounts': snapshot.get('mappedCommonEquityCountryCounts'),
                'mappedCommonEquityCountryWeights': snapshot.get('mappedCommonEquityCountryWeights'),
                'corpPositiveNonCorpNameCount': snapshot.get('corpPositiveNonCorpNameCount'),
            }
            for snapshot in country.get('monthSnapshots', [])
        ],
    }), flush=True)


if __name__ == '__main__':
    main()
