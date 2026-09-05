#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INP = ROOT / 'data/research/sec-legacy-etf-series-source-preid-direct-v29fix2-2006.json'
OUT = ROOT / 'data/research/sec-legacy-etf-series-source-preid-v29canonical-2006.json'
MONTHS = [('2006-01', '2006-01-31'), ('2006-02', '2006-02-28')]
DIRECT = 'DIRECT_EXPLICIT_ETF_CLASS_ASSOCIATION'
BRAND = 'VANGUARD '


def canonical_name(row: dict) -> str:
    name = row['normalizedSeriesName']
    if row.get('binding') == DIRECT and row.get('registrant', '').upper().startswith(BRAND):
        return name if name.startswith(BRAND) else BRAND + name
    return name


def legacy_id(cik: str, normalized_name: str) -> str:
    digest = hashlib.sha1(normalized_name.encode()).hexdigest()[:12].upper()
    return f'LEGACY:{cik}:{digest}'


def display_name(observed: str, canonical_norm: str) -> str:
    if canonical_norm.startswith(BRAND) and not observed.upper().startswith(BRAND):
        return 'Vanguard ' + observed
    return observed


def main() -> None:
    d = json.loads(INP.read_text())
    positives = d['positiveIdentities']
    occurrences = d['sourceOccurrences']

    id_map = {}
    canonical_norm_by_old = {}
    groups = defaultdict(list)
    for row in positives:
        cname = canonical_name(row)
        cid = legacy_id(row['cik'], cname)
        id_map[row['legacyIdentity']] = cid
        canonical_norm_by_old[row['legacyIdentity']] = cname
        groups[cid].append(row)

    # A canonical collision is allowed only for the exact, direct-bound Vanguard
    # leading-brand alias pair: "X" and "VANGUARD X" under the same CIK.
    collision_audit = []
    for cid, rows in sorted(groups.items()):
        if len(rows) <= 1:
            continue
        ciks = {r['cik'] for r in rows}
        cnames = {canonical_name(r) for r in rows}
        if len(ciks) != 1 or len(cnames) != 1 or any(r.get('binding') != DIRECT for r in rows):
            raise RuntimeError(f'unsafe canonical collision {cid}: {[(r["cik"], r["normalizedSeriesName"], r.get("binding")) for r in rows]}')
        cname = next(iter(cnames))
        allowed = {cname, cname[len(BRAND):] if cname.startswith(BRAND) else cname}
        observed = {r['normalizedSeriesName'] for r in rows}
        if not observed.issubset(allowed) or len(rows) != 2:
            raise RuntimeError(f'non-pair/non-leading-brand collision {cid}: {sorted(observed)}')
        collision_audit.append({
            'canonicalLegacyIdentity': cid,
            'cik': rows[0]['cik'],
            'canonicalNormalizedSeriesName': cname,
            'observedNormalizedSeriesNames': sorted(observed),
            'memberLegacyIdentities': sorted(r['legacyIdentity'] for r in rows),
        })

    canonical_positives = []
    synthetic_count = 0
    for cid, rows in sorted(groups.items()):
        cname = canonical_name(rows[0])
        # Prefer an actually observed canonical-prefixed title. If it does not
        # exist (e.g. European Stock Index Fund), synthesize only the identity
        # label; source occurrences keep the original observed schedule title.
        ordered = sorted(
            rows,
            key=lambda r: (
                r['normalizedSeriesName'] != cname,
                r['evidenceDateFiled'],
                r['sourceFilingDate'],
                r['legacyIdentity'],
            ),
        )
        rep = deepcopy(ordered[0])
        observed_names = sorted({r['seriesName'] for r in rows})
        observed_norms = sorted({r['normalizedSeriesName'] for r in rows})
        rep['legacyIdentity'] = cid
        if rep['normalizedSeriesName'] != cname:
            rep['sourceObservedSeriesName'] = rep['seriesName']
            rep['seriesName'] = display_name(rep['seriesName'], cname)
            rep['normalizedSeriesName'] = cname
            synthetic_count += 1
        if len(rows) > 1 or observed_norms != [cname]:
            rep['identityCanonicalizationRule'] = 'DIRECT_VANGUARD_REGISTRANT_EXACT_LEADING_BRAND'
            rep['identityObservedSeriesNames'] = observed_names
            rep['identityObservedNormalizedSeriesNames'] = observed_norms
        canonical_positives.append(rep)

    canonical_occurrences = []
    remapped_occurrence_count = 0
    for row in occurrences:
        old_id = row['legacyIdentity']
        new_id = id_map.get(old_id)
        if not new_id:
            raise RuntimeError(f'occurrence references unknown legacy identity {old_id}')
        rec = deepcopy(row)
        if new_id != old_id:
            rec['sourceObservedLegacyIdentity'] = old_id
            rec['legacyIdentity'] = new_id
            remapped_occurrence_count += 1
        canonical_occurrences.append(rec)

    # Rebuild PIT snapshots from remapped identities while preserving the exact
    # source-observed title used to bind each schedule.
    snapshots = []
    for month, asof in MONTHS:
        latest = {}
        for row in canonical_occurrences:
            if row['sourceFilingDate'] > asof or row['evidenceDateFiled'] > asof:
                continue
            cur = latest.get(row['legacyIdentity'])
            if cur is None or (row['sourceFilingDate'], row.get('sourceAccession') or '') > (cur['sourceFilingDate'], cur.get('sourceAccession') or ''):
                latest[row['legacyIdentity']] = row
        src = sorted(latest.values(), key=lambda x: (x['cik'], x['normalizedSeriesName'], x['legacyIdentity']))
        snapshots.append({'signalMonth': month, 'asOf': asof, 'sourceSeriesCount': len(src), 'sourceFilings': src})

    binding_counts = Counter(r['binding'] for r in canonical_positives)
    source_form_counts = Counter(r['sourceForm'] for r in canonical_occurrences)
    canonicalized_identity_count = sum(1 for r in positives if id_map[r['legacyIdentity']] != r['legacyIdentity'])
    out = {**d}
    out.update({
        'purpose': (
            'Strict pre-Series-ID complete-portfolio ETF source catalog after same-original-line direct class repair and '
            'a deterministic pre-ID-only Vanguard identity normalization. Only identities already accepted by direct '
            'Series/class evidence under a registrant whose name begins VANGUARD are normalized, and only by adding an '
            'exact leading VANGUARD token when absent. No post-ID Series/Class metadata, ticker, fuzzy/edit-distance name '
            'matching, holdings, ranks, returns, or strategy outcomes are used. Source occurrences retain their exact '
            'observed schedule titles; only the legacy identity key is canonicalized.'
        ),
        'identityCanonicalizationRule': 'DIRECT_VANGUARD_REGISTRANT_EXACT_LEADING_BRAND',
        'identityCanonicalizationCollisionCount': len(collision_audit),
        'identityCanonicalizationCollisions': collision_audit,
        'canonicalizedInputIdentityCount': canonicalized_identity_count,
        'syntheticCanonicalLabelCount': synthetic_count,
        'remappedSourceOccurrenceCount': remapped_occurrence_count,
        'preCanonicalPositiveIdentityCount': len(positives),
        'positiveIdentityCount': len(canonical_positives),
        'positiveIdentities': sorted(canonical_positives, key=lambda x: x['legacyIdentity']),
        'sourceOccurrenceCount': len(canonical_occurrences),
        'sourceOccurrences': sorted(canonical_occurrences, key=lambda x: (x['legacyIdentity'], x['sourceFilingDate'], x.get('sourceAccession') or '')),
        'bindingCounts': dict(sorted(binding_counts.items())),
        'sourceFormCounts': dict(sorted(source_form_counts.items())),
        'monthSnapshots': snapshots,
    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({
        'preCanonicalPositiveIdentityCount': len(positives),
        'positiveIdentityCount': len(canonical_positives),
        'sourceOccurrenceCount': len(canonical_occurrences),
        'canonicalizedInputIdentityCount': canonicalized_identity_count,
        'collisionCount': len(collision_audit),
        'syntheticCanonicalLabelCount': synthetic_count,
        'bindingCounts': dict(sorted(binding_counts.items())),
        'monthSnapshots': [{'signalMonth': s['signalMonth'], 'sourceSeriesCount': s['sourceSeriesCount']} for s in snapshots],
    }, indent=2))


if __name__ == '__main__':
    main()
