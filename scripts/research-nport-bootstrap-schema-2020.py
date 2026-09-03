#!/usr/bin/env python3
from __future__ import annotations
import gzip, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
OUT=ROOT/'data'/'research'/'nport-bootstrap-schema-2020.json'

with gzip.open(SRC,'rt',encoding='utf-8') as f:
    p=json.load(f)
rows=p.get('snapshots') or p.get('filings') or []
r20=[r for r in rows if str(r.get('reportDate') or '').startswith('2020-') or str(r.get('filingDate') or '').startswith('2020-')]
key_counts=Counter(k for r in r20 for k,v in r.items() if v not in (None,'',[],{}))
identity_keys=['seriesId','seriesName','registrantName','company','cik','accession','filingDate','reportDate','form','sourceFilename']
samples=[]
seen=set()
for r in r20:
    sid=str(r.get('seriesId') or '')
    if not sid or sid in seen: continue
    seen.add(sid)
    samples.append({k:r.get(k) for k in identity_keys if k in r})
    if len(samples)>=80: break
out={
    'purpose':'Inspect only frozen N-PORT structural identity fields available for building a network-independent 2020 legacy overlap inventory. No prices, returns, ranks, or strategy outputs are used.',
    'rowCount':len(r20),
    'nonEmptyKeyCounts':dict(sorted(key_counts.items())),
    'identitySamples':samples,
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2),flush=True)
