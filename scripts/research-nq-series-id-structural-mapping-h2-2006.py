#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/research/nq-pit-holdings-series-id-h2-2006.json'
OUT = ROOT / 'data/research/nq-series-id-structural-mapping-h2-2006.json'
HOLDINGS_RUN_ID = 34179821383
HOLDINGS_ARTIFACT_ID = 10038557328
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
    module = load_module(
        'authoritative_h1_catalog_mapping',
        ROOT / 'scripts/research-nq-catalog-structural-mapping-h1-2006.py',
    )
    module.RAW = RAW
    module.OUT = OUT
    module.main()

    result = json.loads(OUT.read_text())
    result['purpose'] = (
        'H2 2006 deterministic structural security mapping after retaining only holdings explicitly attributed '
        'to COMMON_EQUITY sections. The exact H1 authoritative mapping implementation is reused unchanged with '
        'H2 holdings artifact 10038557328 and frozen N-PX master artifact 9876020712. No fuzzy/edit-distance '
        'candidate is auto-accepted. No country defaulting, rank, return, or strategy outcome is used.'
    )
    result['holdingsRunId'] = HOLDINGS_RUN_ID
    result['holdingsArtifactId'] = HOLDINGS_ARTIFACT_ID
    result['authoritativeH1MappingRunId'] = AUTHORITATIVE_H1_MAPPING_RUN_ID
    result['authoritativeH1MappingArtifactId'] = AUTHORITATIVE_H1_MAPPING_ARTIFACT_ID
    result['npxArtifactId'] = NPX_ARTIFACT_ID
    OUT.write_text(json.dumps(result, indent=2) + '\n')

    print('H2_MAPPING_SUMMARY', json.dumps({
        'holdingsArtifactId': HOLDINGS_ARTIFACT_ID,
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
