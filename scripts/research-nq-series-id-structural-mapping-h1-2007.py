#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/research/nq-pit-holdings-series-id-h1-2007.json'
OUT = ROOT / 'data/research/nq-series-id-structural-mapping-h1-2007.json'
AUTHORITATIVE_H1_MAPPING_RUN_ID = 34090287022
AUTHORITATIVE_H1_MAPPING_ARTIFACT_ID = 10006580498
NPX_ARTIFACT_ID = 9876020712


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    holdings_run_id = int(os.environ['HOLDINGS_RUN_ID'])
    holdings_artifact_id = int(os.environ['HOLDINGS_ARTIFACT_ID'])
    if holdings_run_id <= 0 or holdings_artifact_id <= 0:
        raise RuntimeError('HOLDINGS_RUN_ID and HOLDINGS_ARTIFACT_ID must be positive')

    module = load_module(
        'authoritative_h1_catalog_mapping',
        ROOT / 'scripts/research-nq-catalog-structural-mapping-h1-2006.py',
    )
    module.RAW = RAW
    module.OUT = OUT
    module.main()

    result = json.loads(OUT.read_text())
    result['purpose'] = (
        'H1 2007 deterministic structural security mapping after retaining only holdings explicitly attributed '
        'to COMMON_EQUITY sections. The exact H1 authoritative mapping implementation is reused unchanged with '
        'the validated H1 2007 holdings artifact and frozen 2006 N-PX security master artifact 9876020712. '
        'The 2006 N-PX master remains the latest PIT annual proxy-voting security master available before all H1 2007 '
        'signal dates. No fuzzy/edit-distance candidate is auto-accepted. No country defaulting, rank, return, or '
        'strategy outcome is used.'
    )
    result['holdingsRunId'] = holdings_run_id
    result['holdingsArtifactId'] = holdings_artifact_id
    result['authoritativeH1MappingRunId'] = AUTHORITATIVE_H1_MAPPING_RUN_ID
    result['authoritativeH1MappingArtifactId'] = AUTHORITATIVE_H1_MAPPING_ARTIFACT_ID
    result['npxArtifactId'] = NPX_ARTIFACT_ID
    OUT.write_text(json.dumps(result, indent=2) + '\n')

    print('H1_2007_MAPPING_SUMMARY', json.dumps({
        'holdingsRunId': holdings_run_id,
        'holdingsArtifactId': holdings_artifact_id,
        'npxArtifactId': NPX_ARTIFACT_ID,
        'matchMethodCounts': result['matchMethodCounts'],
        'monthly': [
            {
                'signalMonth': s['signalMonth'],
                'sourceSeriesCount': s['sourceSeriesCount'],
                'commonEquityHoldingCount': s['commonEquityHoldingCount'],
                'uniqueMappedCount': s['uniqueMappedCount'],
                'uniqueMappedCountRate': s['uniqueMappedCountRate'],
                'uniqueMappedWeightRate': s['uniqueMappedWeightRate'],
                'ambiguousCount': s['ambiguousCount'],
                'unmappedCount': s['unmappedCount'],
            }
            for s in result['monthSnapshots']
        ],
    }), flush=True)


if __name__ == '__main__':
    main()
