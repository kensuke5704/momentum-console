#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'nport-us-equity-fixture-inventory-2020.json'

MIN_HOLDINGS = 20

with gzip.open(BOOTSTRAP, 'rt', encoding='utf-8') as f:
    bp = json.load(f)
rows = bp.get('snapshots') or bp.get('filings') or []

# Keep one snapshot per (series, report date), preferring the latest public filing.
latest = {}
for r in rows:
    sid = str(r.get('seriesId') or '').strip()
    report = str(r.get('reportDate') or '')
    filed = str(r.get('filingDate') or '')
    if not sid or not report.startswith('2020-'):
        continue
    key = (sid, report)
    prev = latest.get(key)
    if prev is None or (filed, str(r.get('accession') or '')) > (str(prev.get('filingDate') or ''), str(prev.get('accession') or '')):
        latest[key] = r

candidates = []
for (sid, report), r in sorted(latest.items()):
    holdings = r.get('holdings') or []
    if len(holdings) < MIN_HOLDINGS:
        continue
    candidates.append({
        'seriesId': sid,
        'seriesName': r.get('seriesName'),
        'reportDate': report,
        'filingDate': r.get('filingDate'),
        'holdingCount': len(holdings),
        'registrantName': r.get('registrantName') or r.get('registrant') or r.get('companyName') or r.get('company'),
        'cik': r.get('cik') or r.get('registrantCik'),
        'accession': r.get('accession'),
    })

# Group only on metadata already present in the frozen bootstrap. No parser-success,
# price, return, rank, or strategy-performance information is used.
groups = defaultdict(list)
for x in candidates:
    group_key = (
        str(x.get('cik') or ''),
        str(x.get('registrantName') or ''),
        x['reportDate'],
    )
    groups[group_key].append(x)

group_rows = []
for (cik, registrant, report), rr in groups.items():
    rr = sorted(rr, key=lambda x: (str(x.get('seriesName') or ''), x['seriesId']))
    group_rows.append({
        'cik': cik or None,
        'registrantName': registrant or None,
        'reportDate': report,
        'qualifyingSeries': len(rr),
        'medianHoldingCount': sorted(x['holdingCount'] for x in rr)[len(rr)//2],
        'series': rr,
    })

group_rows.sort(key=lambda g: (-g['qualifyingSeries'], g['reportDate'], str(g.get('registrantName') or ''), str(g.get('cik') or '')))

out = {
    'year': 2020,
    'purpose': 'Deterministically inventory frozen N-PORT series suitable for legacy reproducibility fixtures using only structural US-equity holding availability.',
    'selectionRule': f'2020 N-PORT snapshot with at least {MIN_HOLDINGS} Production-eligible holdings; grouped by available registrant metadata and reportDate; sorted by qualifying series count then deterministic text keys.',
    'minimumHoldings': MIN_HOLDINGS,
    'candidateSnapshots': len(candidates),
    'groups': group_rows[:100],
    'topCandidates': candidates[:200],
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')

print('CANDIDATE_SNAPSHOTS', len(candidates))
print('TOP_GROUPS', json.dumps([{k:v for k,v in g.items() if k != 'series'} for g in group_rows[:20]], sort_keys=True))
for g in group_rows[:10]:
    print('GROUP', json.dumps({
        'cik': g['cik'], 'registrantName': g['registrantName'], 'reportDate': g['reportDate'],
        'qualifyingSeries': g['qualifyingSeries'],
        'series': [{'seriesId':x['seriesId'],'seriesName':x['seriesName'],'holdingCount':x['holdingCount']} for x in g['series'][:30]],
    }, sort_keys=True))
