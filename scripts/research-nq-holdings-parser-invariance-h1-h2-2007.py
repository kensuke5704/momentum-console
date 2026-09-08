#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'
H1_HOLDINGS = DATA / 'nq-pit-holdings-series-id-h1-2007.json'
H2_HOLDINGS = DATA / 'nq-pit-holdings-series-id-h2-2007.json'
H1_SOURCE = DATA / 'sec-id-era-strict-series-source-h1-2007.json'
H2_SOURCE = DATA / 'sec-id-era-strict-series-source-h2-2007.json'
OUT = DATA / 'nq-holdings-parser-invariance-h1-h2-2007.json'


def filing_key(row: dict) -> tuple[str, str, str]:
    return (
        row.get('seriesId') or row.get('canonicalIdentity') or '',
        row.get('accession') or '',
        row.get('sourceFilename') or row.get('filename') or '',
    )


def unique_holdings_records(payload: dict) -> dict[tuple[str, str, str], dict]:
    out = {}
    for snapshot in payload.get('monthSnapshots', []):
        for row in snapshot.get('sourceFilings', []):
            if row.get('identityRegime') != 'SERIES_ID':
                continue
            key = filing_key(row)
            if not all(key):
                raise RuntimeError(f'incomplete Series-ID holdings filing key: {key}')
            previous = out.get(key)
            if previous is not None and previous != row:
                raise RuntimeError(f'same holdings filing key has non-identical repeated record: {key}')
            out[key] = row
    return out


def unique_source_keys(payload: dict) -> set[tuple[str, str, str]]:
    out = set()
    # Parser invariance must be measured only over source snapshots actually supplied
    # to each current-period holdings run. Closed-history replay snapshots in the H2
    # source catalog were not inputs to the H2 holdings extraction and are excluded.
    snapshots = list(payload.get('monthSnapshots', []))
    for snapshot in snapshots:
        for row in snapshot.get('sourceFilings', []):
            key = filing_key(row)
            if not all(key):
                raise RuntimeError(f'incomplete source-catalog filing key: {key}')
            out.add(key)
    return out


def parser_semantic_view(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != 'legacyIdentity'}


def main() -> None:
    h1 = json.loads(H1_HOLDINGS.read_text())
    h2 = json.loads(H2_HOLDINGS.read_text())
    h1_source = json.loads(H1_SOURCE.read_text())
    h2_source = json.loads(H2_SOURCE.read_text())

    left = unique_holdings_records(h1)
    right = unique_holdings_records(h2)
    holdings_overlap = sorted(set(left) & set(right))
    source_overlap = sorted(unique_source_keys(h1_source) & unique_source_keys(h2_source))

    semantic_mismatches = []
    legacy_identity_differences = []
    exact_full_record_matches = 0
    for key in holdings_overlap:
        lrow = left[key]
        rrow = right[key]
        if lrow == rrow:
            exact_full_record_matches += 1
        elif lrow.get('legacyIdentity') != rrow.get('legacyIdentity'):
            legacy_identity_differences.append({
                'seriesId': key[0],
                'accession': key[1],
                'sourceFilename': key[2],
                'h1LegacyIdentity': lrow.get('legacyIdentity'),
                'h2LegacyIdentity': rrow.get('legacyIdentity'),
            })
        lv = parser_semantic_view(lrow)
        rv = parser_semantic_view(rrow)
        if lv != rv:
            semantic_mismatches.append({
                'seriesId': key[0],
                'accession': key[1],
                'sourceFilename': key[2],
                'differingFields': sorted(
                    field for field in set(lv) | set(rv)
                    if lv.get(field) != rv.get(field)
                ),
            })

    source_only_missing_from_holdings_overlap = sorted(set(source_overlap) - set(holdings_overlap))
    holdings_overlap_not_in_source_overlap = sorted(set(holdings_overlap) - set(source_overlap))
    passed = bool(
        source_overlap
        and set(holdings_overlap) == set(source_overlap)
        and not semantic_mismatches
    )

    report = {
        'purpose': (
            'Parser-invariance audit across validated H1-2007 and H2-2007 Series-ID raw holdings. '
            'The expected overlap is derived independently from the current-period strict source snapshots actually '
            'supplied to the two holdings runs; every shared Series-ID + accession + SEC source-file key must appear '
            'in both holdings artifacts and every parser-derived field must be exact after excluding only '
            'legacyIdentity schema metadata.'
        ),
        'auditSetCorrection': 'docs/research/h2-2007-parser-invariance-audit-set-correction.md',
        'h1UniqueHoldingsFilingRecordCount': len(left),
        'h2UniqueHoldingsFilingRecordCount': len(right),
        'sourceCatalogOverlapCount': len(source_overlap),
        'holdingsOverlapCount': len(holdings_overlap),
        'exactFullRecordMatchCount': exact_full_record_matches,
        'legacyIdentityOnlyDifferenceCount': len(legacy_identity_differences),
        'semanticMismatchCount': len(semantic_mismatches),
        'sourceOnlyMissingFromHoldingsOverlapCount': len(source_only_missing_from_holdings_overlap),
        'holdingsOverlapNotInSourceOverlapCount': len(holdings_overlap_not_in_source_overlap),
        'legacyIdentityOnlyDifferences': legacy_identity_differences,
        'semanticMismatches': semantic_mismatches,
        'sourceOnlyMissingFromHoldingsOverlap': [list(k) for k in source_only_missing_from_holdings_overlap],
        'holdingsOverlapNotInSourceOverlap': [list(k) for k in holdings_overlap_not_in_source_overlap],
        'passed': passed,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + '\n')
    print('PARSER_INVARIANCE_H1_H2_2007', json.dumps({
        key: report[key] for key in (
            'h1UniqueHoldingsFilingRecordCount',
            'h2UniqueHoldingsFilingRecordCount',
            'sourceCatalogOverlapCount',
            'holdingsOverlapCount',
            'exactFullRecordMatchCount',
            'legacyIdentityOnlyDifferenceCount',
            'semanticMismatchCount',
            'sourceOnlyMissingFromHoldingsOverlapCount',
            'holdingsOverlapNotInSourceOverlapCount',
            'passed',
        )
    }), flush=True)
    if not passed:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
