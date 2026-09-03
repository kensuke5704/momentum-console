#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'production-nport-registrant-inventory-2020.json'


def cik_from_accession(accession: str) -> str | None:
    digits = re.sub(r'\D', '', str(accession or ''))
    if len(digits) < 10:
        return None
    return str(int(digits[:10]))


with gzip.open(BOOT, 'rt', encoding='utf-8') as f:
    bp = json.load(f)
rows = bp.get('snapshots') or bp.get('filings') or []
by_cik: dict[str, dict] = {}
series_seen = set()
for row in rows:
    if not str(row.get('reportDate') or '').startswith('2020'):
        continue
    sid = str(row.get('seriesId') or '')
    accession = str(row.get('accession') or '')
    cik = cik_from_accession(accession)
    if not sid or not cik:
        continue
    series_seen.add(sid)
    g = by_cik.setdefault(cik, {'cik': cik, 'seriesIds': set(), 'seriesNames': set(), 'accessions': set(), 'reportDates': set(), 'filingDates': set()})
    g['seriesIds'].add(sid)
    if row.get('seriesName'): g['seriesNames'].add(str(row['seriesName']))
    g['accessions'].add(accession)
    if row.get('reportDate'): g['reportDates'].add(str(row['reportDate']))
    if row.get('filingDate'): g['filingDates'].add(str(row['filingDate']))

registrants = []
for g in by_cik.values():
    registrants.append({
        'cik': g['cik'],
        'seriesCount': len(g['seriesIds']),
        'seriesIds': sorted(g['seriesIds']),
        'seriesNames': sorted(g['seriesNames']),
        'nportAccessions': sorted(g['accessions']),
        'reportDates': sorted(g['reportDates']),
        'filingDates': sorted(g['filingDates']),
    })
registrants.sort(key=lambda g: (-g['seriesCount'], int(g['cik'])))
out = {
    'year': 2020,
    'purpose': 'Group the exact Production N-PORT bootstrap series by registrant CIK for deterministic legacy shareholder-report coverage planning. No prices, returns, parser success, or strategy outputs used.',
    'productionSeriesCount': len(series_seen),
    'registrantCount': len(registrants),
    'registrants': registrants,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + '\n')
print('SUMMARY', json.dumps({'productionSeriesCount': len(series_seen), 'registrantCount': len(registrants)}))
for g in registrants[:30]:
    print('REGISTRANT', g['cik'], 'series', g['seriesCount'], 'reports', g['reportDates'], 'examples', g['seriesNames'][:4])
