#!/usr/bin/env python3
from __future__ import annotations

import difflib
import gzip
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fast', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-fast-2020.py')
fast = importlib.util.module_from_spec(spec); spec.loader.exec_module(fast)
repro = fast.repro

fixture = {
    'company': 'First Trust Exchange-Traded Fund VI',
    'dateFiled': '2020-12-07',
    'filename': 'edgar/data/1552740/0001445546-20-005815.txt',
}
transport, submission = repro.ov.fetch_full_filing(repro.ov.seg.meta.sec_url(fixture['filename']))
rm = repro.ov.REPORT_DATE.search(submission)
report = repro.ov.iso8(rm.group(1) if rm else None)
series = fast.shared_nport_series_contracts('', fixture['company'])
mapped = fast.structural_mapped_modern_series(repro.ov.embedded_csr(submission), series)

with gzip.open(repro.BOOTSTRAP, 'rt', encoding='utf-8') as f:
    bp = json.load(f)
nport = bp.get('snapshots') or bp.get('filings') or []
by_series = defaultdict(list)
for row in nport:
    if row.get('seriesId') and row.get('reportDate'):
        by_series[row['seriesId']].append(row)

out = {'transport': transport, 'reportDate': report, 'series': []}
for sid in ('S000053943', 'S000053948', 'S000058146'):
    legacy = mapped.get(sid)
    if not legacy:
        continue
    nearest = min(by_series[sid], key=lambda f: repro.days_between(report, f['reportDate']))
    unique_map = repro.unique_alias_symbol_map(nearest.get('holdings', []))
    nport_names = []
    for h in nearest.get('holdings', []):
        issuer = str(h.get('issuerName') or '')
        nport_names.append((repro.ov.norm_issuer(issuer), issuer, str(h.get('symbol') or '')))
    diag = []
    for h in sorted(legacy['holdings'], key=lambda x: -float(x.get('weight') or 0)):
        desc = str(h.get('description') or '')
        aliases = repro.issuer_aliases(desc)
        symbol = next((unique_map[a] for a in aliases if a in unique_map), None)
        if symbol:
            continue
        q = repro.ov.norm_issuer(desc)
        close = sorted(
            ((difflib.SequenceMatcher(None, q, norm).ratio(), issuer, ticker, norm) for norm, issuer, ticker in nport_names),
            reverse=True,
        )[:3]
        diag.append({
            'description': desc,
            'weight': h.get('weight'),
            'normalized': q,
            'aliases': aliases,
            'closestNport': [
                {'similarity': round(sim, 4), 'issuerName': issuer, 'symbol': ticker, 'normalized': norm}
                for sim, issuer, ticker, norm in close
            ],
        })
    out['series'].append({
        'seriesId': sid,
        'seriesName': legacy.get('seriesName'),
        'legacyHoldingCount': len(legacy['holdings']),
        'nportHoldingCount': len(nearest.get('holdings', [])),
        'unmatchedWeight': sum(float(x.get('weight') or 0) for x in diag),
        'topUnmatched': diag[:20],
    })

path = ROOT / 'data' / 'research' / 'first-trust-issuer-gap-diagnostic-2020.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2), flush=True)
