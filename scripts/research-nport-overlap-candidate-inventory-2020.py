#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'nport-overlap-candidate-inventory-2020.json'

with gzip.open(P, 'rt', encoding='utf-8') as f:
    d = json.load(f)
rows = d.get('snapshots') or d.get('filings') or []
by = {}
for x in rows:
    rd = str(x.get('reportDate') or '')
    if not rd.startswith('2020'):
        continue
    sid = str(x.get('seriesId') or '')
    if not sid:
        continue
    r = by.setdefault(sid, {
        'seriesId': sid,
        'seriesName': x.get('seriesName'),
        'reports': [],
        'holdingCountMax': 0,
    })
    r['seriesName'] = r['seriesName'] or x.get('seriesName')
    r['reports'].append({'reportDate': x.get('reportDate'), 'filingDate': x.get('filingDate')})
    r['holdingCountMax'] = max(r['holdingCountMax'], len(x.get('holdings', [])))

vals = sorted(by.values(), key=lambda r: ((r.get('seriesName') or ''), r['seriesId']))
patterns = {
    'FIRST_TRUST': re.compile(r'FIRST TRUST', re.I),
    'ISHARES': re.compile(r'ISHARES', re.I),
    'INVESCO_POWERSHARES': re.compile(r'INVESCO|POWERSHARES', re.I),
    'PROSHARES': re.compile(r'PROSHARES', re.I),
    'SPDR': re.compile(r'SPDR|STREETTRACKS', re.I),
    'VANGUARD': re.compile(r'VANGUARD', re.I),
}
family_counts = Counter()
for r in vals:
    name = str(r.get('seriesName') or '')
    matched = False
    for family, pat in patterns.items():
        if pat.search(name):
            family_counts[family] += 1
            matched = True
    if not matched:
        family_counts['OTHER'] += 1

out = {
    'year': 2020,
    'purpose': 'Inventory the exact committed Production bootstrap N-PORT series universe available for structural legacy reproducibility testing. No prices or returns used.',
    'source': 'data/sec-nport/bootstrap.json.gz',
    'seriesCount': len(vals),
    'familyNameHintCounts': dict(sorted(family_counts.items())),
    'series': vals,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + '\n')
print('SUMMARY', json.dumps({k: v for k, v in out.items() if k != 'series'}, sort_keys=True))
print('SERIES_COUNT', len(vals))
for r in vals:
    name = str(r.get('seriesName') or '')
    if re.search(r'SPDR|ISHARES|INVESCO|POWERSHARES|PROSHARES|FIRST TRUST|VANGUARD|ETF', name, re.I):
        print(json.dumps(r, sort_keys=True))
