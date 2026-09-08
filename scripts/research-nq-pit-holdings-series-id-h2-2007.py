#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/research'
SOURCE = DIR / 'sec-id-era-strict-series-source-h2-2007.json'
ADAPTED = DIR / 'sec-id-era-strict-series-source-h2-2007-holdings-adapter.json'
OUT = DIR / 'nq-pit-holdings-series-id-h2-2007.json'
AUTHORITATIVE_H1_HOLDINGS_RUN_ID = 34089965073
AUTHORITATIVE_H1_HOLDINGS_ARTIFACT_ID = 10006530879


def norm(raw: str | None) -> str:
    return ' '.join(re.sub(r'[^A-Z0-9]+', ' ', raw.upper() if raw else '').split())


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def adapt_source_catalog(source: dict, source_artifact_id: int) -> dict:
    months = []
    for snap in source['monthSnapshots']:
        rows = []
        for row in snap['sourceFilings']:
            sid = row['seriesId']
            rows.append({
                **row,
                'canonicalIdentity': sid,
                'identityRegime': 'SERIES_ID',
                'legacyIdentity': None,
                'normalizedSeriesName': norm(row.get('seriesName')),
            })
        months.append({
            **snap,
            'legacySourceCount': 0,
            'seriesIdSourceCount': snap['sourceSeriesCount'],
            'sourceFilings': rows,
        })
    return {
        'purpose': 'Mechanical Series-ID-only schema adapter for the validated H2 2007 strict source catalog. No source is added, removed, renamed, bridged, or inferred.',
        'sourceCatalogArtifactId': source_artifact_id,
        'monthSnapshots': months,
    }


def main() -> None:
    source_artifact_id = int(os.environ['SOURCE_CATALOG_ARTIFACT_ID'])
    if source_artifact_id <= 0:
        raise RuntimeError('SOURCE_CATALOG_ARTIFACT_ID must be positive')
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    adapted = adapt_source_catalog(source, source_artifact_id)
    ADAPTED.write_text(json.dumps(adapted, indent=2) + '\n')

    extractor = load_module(
        'authoritative_h1_holdings_extractor',
        ROOT / 'scripts/research-nq-pit-holdings-hybrid-h1-2006.py',
    )
    extractor.CATALOG = ADAPTED
    extractor.OUT = OUT
    extractor.SOURCE_CATALOG_RUN_ID = None
    extractor.main()

    result = json.loads(OUT.read_text())
    result['purpose'] = (
        'H2 2007 Series-ID source-catalog-driven raw complete-portfolio holdings extraction. '
        'The exact authoritative H1 holdings extractor from run 34089965073 is reused unchanged; only a mechanical '
        'Series-ID schema adapter and output path are changed. Holdings content never determines source identity. '
        'No ticker, fuzzy matching, rank, return, or strategy outcome is used.'
    )
    result['sourceCatalogArtifactId'] = source_artifact_id
    result['sourceCatalogSha256'] = source_sha
    result['authoritativeH1HoldingsRunId'] = AUTHORITATIVE_H1_HOLDINGS_RUN_ID
    result['authoritativeH1HoldingsArtifactId'] = AUTHORITATIVE_H1_HOLDINGS_ARTIFACT_ID
    result['schemaAdapterPath'] = str(ADAPTED.relative_to(ROOT))
    result['sourceCatalogPath'] = str(SOURCE.relative_to(ROOT))
    result['legacyRequestedIdentityCount'] = 0
    result['monthlySourceSeriesAppearanceCount'] = sum(
        len(s['sourceFilings']) for s in source['monthSnapshots']
    )
    OUT.write_text(json.dumps(result, indent=2) + '\n')

    print('H2_2007_HOLDINGS_SUMMARY', json.dumps({
        'sourceCatalogArtifactId': source_artifact_id,
        'sourceCatalogSha256': source_sha,
        'uniqueSourceFilingCount': result['uniqueSourceFilingCount'],
        'filingFetchSuccessCount': result['filingFetchSuccessCount'],
        'filingFetchErrorCount': result['filingFetchErrorCount'],
        'uniqueParsedHoldingCount': result['uniqueParsedHoldingCount'],
        'seriesIdRequestedIdentityCount': result['seriesIdRequestedIdentityCount'],
        'monthlySourceSeriesAppearanceCount': result['monthlySourceSeriesAppearanceCount'],
        'monthly': [
            {
                'signalMonth': s['signalMonth'],
                'catalog': s['catalogSourceSeriesCount'],
                'records': len(s['sourceFilings']),
                'parsed': s['parsedSourceSeriesCount'],
                'missing': len(s['missingParsedSeries']),
            }
            for s in result['monthSnapshots']
        ],
    }), flush=True)


if __name__ == '__main__':
    main()
