#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'production-series-manifest-2020.json'

with gzip.open(BOOT, 'rt', encoding='utf-8') as f:
    bp = json.load(f)
rows = bp.get('snapshots') or bp.get('filings') or []

by_sid = defaultdict(list)
for r in rows:
    if not str(r.get('reportDate') or '').startswith('2020'):
        continue
    sid = str(r.get('seriesId') or '').strip()
    if sid:
        by_sid[sid].append(r)

series = []
for sid, rr in sorted(by_sid.items()):
    names = sorted({str(x.get('seriesName') or '').strip() for x in rr if x.get('seriesName')})
    reports = sorted({str(x.get('reportDate') or '') for x in rr if x.get('reportDate')})
    filings = sorted({str(x.get('filingDate') or '') for x in rr if x.get('filingDate')})
    accessions = sorted({str(x.get('accession') or '') for x in rr if x.get('accession')})
    max_holdings = max((len(x.get('holdings') or []) for x in rr), default=0)
    series.append({
        'seriesId': sid,
        'seriesName': names[-1] if names else None,
        'allSeriesNames': names,
        'reportDates': reports,
        'filingDates': filings,
        'accessions': accessions,
        'snapshotCount': len(rr),
        'maxProductionFilteredHoldingCount': max_holdings,
    })

out = {
    'purpose': 'Immutable structural manifest of every 2020 series present in the frozen Production N-PORT bootstrap. No prices, returns, ranks, or strategy outputs are accessed.',
    'seriesCount': len(series),
    'series': series,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print('SERIES_COUNT', len(series), flush=True)
for x in series:
    print('SERIES', x['seriesId'], '|', x.get('seriesName') or '', '| snapshots', x['snapshotCount'], '| maxHoldings', x['maxProductionFilteredHoldingCount'], flush=True)
