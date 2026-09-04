#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/structural-new-matches-country-2006.json'
OUT = ROOT / 'data/research/structural-new-matches-submission-header-country-2006.json'

FLAT_SPEC = importlib.util.spec_from_file_location(
    'flat', ROOT / 'scripts' / 'research-sec-submission-header-country-pilot-2006.py'
)
flat = importlib.util.module_from_spec(FLAT_SPEC)
FLAT_SPEC.loader.exec_module(flat)

STRUCT_SPEC = importlib.util.spec_from_file_location(
    'structural', ROOT / 'scripts' / 'research-nq-npx-structural-mapping-2006.py'
)
structural = importlib.util.module_from_spec(STRUCT_SPEC)
STRUCT_SPEC.loader.exec_module(structural)


def resolve_prior_unknown(row, master_rows):
    # These identities entered the mapping only through the already accepted structural rules.
    # Reuse only that accepted trailing presentation/share-class cleanup for SEC issuer-name
    # reconciliation. Do not add fuzzy/edit-distance aliases or use strategy outcomes.
    forms = structural.cleaned_forms(str(row.get('issuer') or ''))
    attempts = []
    for issuer_form in forms:
        candidate = {**row, 'issuer': issuer_form}
        evidence = flat.resolve(candidate, master_rows)
        attempts.append({
            'issuerForm': issuer_form,
            'classification': evidence.get('classification'),
            'historicalExactCikCount': evidence.get('historicalExactCikCount'),
            'seedCik': evidence.get('seedCik'),
            'seedSource': evidence.get('seedSource'),
        })
        if evidence.get('classification') in {'US', 'NON_US'}:
            return {
                **row,
                **evidence,
                'issuer': row.get('issuer'),
                'countryIdentityFormUsed': issuer_form,
                'structuralCountryIdentityRule': 'ACCEPTED_TRAILING_SUFFIX_CLEANUP_EXACT',
                'countryIdentityAttempts': attempts,
            }
    return {
        **row,
        'classification': 'UNKNOWN',
        'countryIdentityAttempts': attempts,
    }


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
            rec = resolve_prior_unknown(row, master_rows)
            rec['priorClassification'] = 'UNKNOWN'
            if rec.get('classification') in {'US', 'NON_US'}:
                promoted.append(rec)
        refreshed.append(rec)
        print('STRUCTURAL_COUNTRY', json.dumps({
            k: rec.get(k) for k in [
                'ticker', 'securityId', 'issuer', 'countryIdentityFormUsed',
                'aggregateWeight', 'occurrenceCount', 'priorClassification',
                'classification', 'stateCode', 'seedCik', 'seedSource',
                'resolutionSource', 'evidenceForm', 'evidenceDateFiled'
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
            'For issuer-name reconciliation, reuse only the already accepted trailing N-Q footnote, '
            'share-class, and jurisdiction cleanup from the structural mapping rule; each cleaned '
            'form still requires exact historical issuer-form name -> unique CIK evidence and a '
            'historical COMPANY DATA block with the same CIK/name and STATE OF INCORPORATION by the '
            'report date. No fuzzy matching, current state, returns, ranks, or strategy outcomes are used.'
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
