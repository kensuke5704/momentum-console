#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/structural-new-matches-country-2006.json'
OUT = ROOT / 'data/research/structural-new-matches-submission-header-country-2006.json'
SPEC = importlib.util.spec_from_file_location(
    'flat', ROOT / 'scripts' / 'research-sec-submission-header-country-pilot-2006.py'
)
flat = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flat)


def main():
    data = json.loads(SRC.read_text())
    rows = data.get('rows', [])
    unknown = [r for r in rows if r.get('classification') == 'UNKNOWN']
    years = sorted({int(r['asOfReportDate'][:4]) for r in unknown})
    master_rows, transports = flat.base.load_master(years)

    refreshed = []
    promoted = []
    for row in rows:
        old_class = row.get('classification', 'UNKNOWN')
        if old_class in {'US', 'NON_US'}:
            rec = dict(row)
            rec['priorClassificationFrozen'] = True
        else:
            evidence = flat.resolve(row, master_rows)
            rec = {**row, **evidence}
            rec['priorClassification'] = 'UNKNOWN'
            if rec.get('classification') in {'US', 'NON_US'}:
                promoted.append(rec)
        refreshed.append(rec)
        print('STRUCTURAL_COUNTRY', json.dumps({
            k: rec.get(k) for k in [
                'ticker', 'securityId', 'issuer', 'aggregateWeight', 'occurrenceCount',
                'priorClassification', 'classification', 'stateCode', 'seedCik',
                'seedSource', 'resolutionSource', 'evidenceForm', 'evidenceDateFiled'
            ]
        }), flush=True)

    counts = {
        c: sum(1 for r in refreshed if r.get('classification') == c)
        for c in ['US', 'NON_US', 'UNKNOWN']
    }
    weights = {
        c: sum(float(r.get('aggregateWeight') or 0) for r in refreshed if r.get('classification') == c)
        for c in counts
    }
    out = {
        'year': 2006,
        'purpose': (
            'Refresh only the previously UNKNOWN deterministic structural new-match identities '
            'with the validated PIT complete-submission flat-header resolver. Existing US/NON_US '
            'classifications from the frozen structural-country artifact are preserved unchanged. '
            'Promotion requires a historical filing available by the report date and one COMPANY '
            'DATA block containing matching historical issuer name, the same deterministic CIK, and '
            'STATE OF INCORPORATION. No current state, returns, ranks, or strategy outcomes are used.'
        ),
        'sourceStructuralCountryArtifactId': 9903255442,
        'masterYears': years,
        'masterIndexTransports': transports,
        'uniqueIdentityCount': len(refreshed),
        'priorUnknownIdentityCount': len(unknown),
        'promotedIdentityCount': len(promoted),
        'promotedOccurrenceCount': sum(int(r.get('occurrenceCount') or 0) for r in promoted),
        'promotedAggregateWeight': sum(float(r.get('aggregateWeight') or 0) for r in promoted),
        'classificationCounts': counts,
        'classificationWeights': weights,
        'rows': refreshed,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({
        k: v for k, v in out.items() if k not in ('rows', 'masterIndexTransports')
    }), flush=True)


if __name__ == '__main__':
    main()
