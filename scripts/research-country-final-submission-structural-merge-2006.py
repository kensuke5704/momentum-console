#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'data/research'
BASE = D / 'sec-submission-header-country-full-merged-2006.json'
SM = D / 'nq-npx-structural-mapping-2006.json'
SNEW = D / 'structural-new-matches-submission-header-country-2006.json'
OUT = D / 'country-final-submission-structural-merge-2006.json'
ADR_RE = re.compile(
    r'\b(?:ADR|GDR|ADS|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY|DEPOSITARY RECEIPT)\b',
    re.I,
)


def key(row):
    return (
        str(row.get('ticker') or '').upper(),
        str(row.get('securityId') or '').upper(),
    )


def main():
    base = json.loads(BASE.read_text())
    sm = json.loads(SM.read_text())
    snew = json.loads(SNEW.read_text())

    cmap = {}
    source = {}
    conflicts = []
    for row in base.get('identityRows', []):
        k = key(row)
        if k == ('', ''):
            continue
        cmap[k] = row.get('classification', 'UNKNOWN')
        source[k] = row.get('resolutionSource') or 'BASELINE_MAPPED_COUNTRY'

    structural_rows = {key(r): r for r in snew.get('rows', []) if key(r) != ('', '')}
    overlap_count = 0
    for k, row in structural_rows.items():
        new_class = row.get('classification', 'UNKNOWN')
        if k in cmap:
            overlap_count += 1
            old_class = cmap[k]
            if old_class in {'US', 'NON_US'} and new_class in {'US', 'NON_US'} and old_class != new_class:
                conflicts.append({
                    'ticker': k[0],
                    'securityId': k[1],
                    'baselineClassification': old_class,
                    'structuralClassification': new_class,
                })
                continue
            if old_class == 'UNKNOWN' and new_class in {'US', 'NON_US'}:
                cmap[k] = new_class
                source[k] = row.get('resolutionSource') or 'STRUCTURAL_COUNTRY'
        else:
            cmap[k] = new_class
            source[k] = row.get('resolutionSource') or 'STRUCTURAL_COUNTRY'

    counts = Counter()
    weights = defaultdict(float)
    methods = Counter()
    rows = []
    matched_count = 0
    matched_weight = 0.0
    for detail in sm.get('details', []):
        weight = float(detail.get('weight') or 0)
        cls = 'UNKNOWN'
        method = 'UNRESOLVED'
        identities = detail.get('identities') or []
        if detail.get('status') == 'MATCHED_UNIQUE' and len(identities) == 1:
            matched_count += 1
            matched_weight += weight
            k = key(identities[0])
            cls = cmap.get(k, 'UNKNOWN')
            if cls in {'US', 'NON_US'}:
                method = source.get(k) or 'IDENTITY_COUNTRY'
        if cls == 'UNKNOWN' and ADR_RE.search(str(detail.get('description') or '')):
            cls = 'NON_US'
            method = 'EXPLICIT_ADR_GDR'
        counts[cls] += 1
        weights[cls] += weight
        methods[method] += 1
        rows.append({
            'seriesId': detail.get('seriesId'),
            'reportDate': detail.get('reportDate'),
            'description': detail.get('description'),
            'weight': weight,
            'mappingStatus': detail.get('status'),
            'matchMethod': detail.get('matchMethod'),
            'identities': identities,
            'classification': cls,
            'classificationSource': method,
        })

    total_count = len(rows)
    total_weight = sum(weights.values())
    resolved_count = counts['US'] + counts['NON_US']
    resolved_weight = weights['US'] + weights['NON_US']
    base_after = base['after']
    base_count_rate = float(base_after['allEcResolvedCountRate'])
    base_weight_rate = float(base_after['allEcResolvedWeightRate'])
    resolved_count_rate = resolved_count / total_count if total_count else 0.0
    resolved_weight_rate = resolved_weight / total_weight if total_weight else 0.0

    if total_count != 936:
        raise RuntimeError(f'unexpected EC holding denominator: {total_count}')
    expected_weight = sum(float(v) for v in base_after['allEcHoldingClassificationWeights'].values())
    if abs(total_weight - expected_weight) > 1e-7:
        raise RuntimeError(f'EC weight denominator drift: {total_weight} vs {expected_weight}')
    if conflicts:
        raise RuntimeError(f'country classification conflict count: {len(conflicts)}')

    structural_resolved = [
        r for r in snew.get('rows', []) if r.get('classification') in {'US', 'NON_US'}
    ]
    structural_unknown = [
        r for r in snew.get('rows', []) if r.get('classification') == 'UNKNOWN'
    ]
    out = {
        'year': 2006,
        'purpose': (
            'Final holding-level conservative country merge after the validated submission flat-header '
            'resolver and the already accepted deterministic structural identity mapping. Baseline mapped '
            'country classifications come from the frozen 12-shard submission-header merge; newly recovered '
            'structural identities use the refreshed structural-country artifact. Existing resolved evidence '
            'is never overwritten, unresolved remains UNKNOWN, and explicit ADR/GDR is the only holding-level '
            'fallback. No current state, returns, ranks, or strategy outcomes are used.'
        ),
        'inputArtifacts': {
            'baselineSubmissionHeaderCountryArtifactId': 9944538015,
            'structuralMappingArtifactId': 9900708609,
            'structuralSubmissionHeaderCountryArtifactId': None,
        },
        'structuralCountryOverlapWithBaselineIdentityCount': overlap_count,
        'conflictCount': len(conflicts),
        'conflicts': conflicts,
        'totalHoldingCount': total_count,
        'totalHoldingWeight': total_weight,
        'matchedHoldingCount': matched_count,
        'matchedHoldingWeight': matched_weight,
        'classificationCounts': dict(counts),
        'classificationWeights': dict(weights),
        'resolvedCount': resolved_count,
        'resolvedWeight': resolved_weight,
        'resolvedCountRate': resolved_count_rate,
        'resolvedWeightRate': resolved_weight_rate,
        'baselineSubmissionHeaderResolvedCountRate': base_count_rate,
        'baselineSubmissionHeaderResolvedWeightRate': base_weight_rate,
        'resolvedCountRateUpliftFromStructural': resolved_count_rate - base_count_rate,
        'resolvedWeightRateUpliftFromStructural': resolved_weight_rate - base_weight_rate,
        'structuralIdentityCount': len(snew.get('rows', [])),
        'structuralResolvedIdentityCount': len(structural_resolved),
        'structuralResolvedOccurrenceCount': sum(int(r.get('occurrenceCount') or 0) for r in structural_resolved),
        'structuralResolvedAggregateWeight': sum(float(r.get('aggregateWeight') or 0) for r in structural_resolved),
        'structuralRemainingUnknownIdentityCount': len(structural_unknown),
        'structuralRemainingUnknownAggregateWeight': sum(float(r.get('aggregateWeight') or 0) for r in structural_unknown),
        'classificationSources': dict(methods),
        'rows': rows,
    }
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k not in ('rows', 'conflicts')}), flush=True)


if __name__ == '__main__':
    main()
