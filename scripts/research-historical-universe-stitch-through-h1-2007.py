#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'
BASE_2006 = DATA / 'historical-universe-builder-2006.json'
H1_2007 = DATA / 'historical-universe-builder-h1-2007.json'
OUT = DATA / 'historical-universe-builder-through-h1-2007.json'

BUILDER_BLOB = '1357402f34dfea1c1dbdcaac7de5078b680eb5c3'
BASE_2006_ARTIFACT_ID = 10039721939


def main() -> None:
    h1_validation_artifact_id = int(os.environ['H1_2007_VALIDATION_ARTIFACT_ID'])
    if h1_validation_artifact_id <= 0:
        raise RuntimeError('H1_2007_VALIDATION_ARTIFACT_ID must be positive')

    base = json.loads(BASE_2006.read_text())
    h1 = json.loads(H1_2007.read_text())
    for payload in (base, h1):
        assert payload.get('builderGitBlob') == BUILDER_BLOB or payload is h1

    base_months = base.get('monthSnapshots', [])
    h1_months = h1.get('monthSnapshots', [])
    expected_base = [f'2006-{month:02d}' for month in range(1, 13)]
    expected_h1 = [f'2007-{month:02d}' for month in range(1, 7)]
    assert [row.get('signalMonth') for row in base_months] == expected_base
    assert [row.get('signalMonth') for row in h1_months] == expected_h1

    for key in ('eligibilityOrder', 'sourceEligibility', 'breadthRule'):
        assert base.get(key) == h1.get(key), (key, base.get(key), h1.get(key))

    combined = base_months + h1_months
    expected = expected_base + expected_h1
    assert [row.get('signalMonth') for row in combined] == expected
    assert len(combined) == 18
    assert len({row.get('signalMonth') for row in combined}) == 18
    assert all(str(row.get('asOf') or '').startswith(row['signalMonth']) for row in combined)
    assert all(len(row.get('symbols', [])) <= 80 for row in combined)

    output = {
        'purpose': (
            'Frozen validated historical-Universe stitch through H1 2007. It concatenates the closed 2006 full-year '
            'Universe artifact and the independently downstream-validated H1 2007 frozen-builder output without '
            'recomputing source discovery, parsing, mapping, country, eligibility, ranking, or strategy performance.'
        ),
        'builderGitBlob': BUILDER_BLOB,
        'segments': [
            {
                'period': '2006',
                'artifactId': BASE_2006_ARTIFACT_ID,
                'validation': 'validated full-year 2006 stitch',
            },
            {
                'period': '2007-H1',
                'artifactId': h1_validation_artifact_id,
                'validation': 'H1 2007 downstream period-extension exact parity',
            },
        ],
        'eligibilityOrder': base.get('eligibilityOrder'),
        'sourceEligibility': base.get('sourceEligibility'),
        'breadthRule': base.get('breadthRule'),
        'monthSnapshots': combined,
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n')
    print('STITCH_THROUGH_H1_2007', json.dumps({
        'months': len(combined),
        'first': combined[0]['signalMonth'],
        'last': combined[-1]['signalMonth'],
        'eligibleSourceSeriesCounts': [row.get('eligibleSourceSeriesCount') for row in combined],
        'universeSizes': [len(row.get('symbols', [])) for row in combined],
    }, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
