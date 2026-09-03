#!/usr/bin/env python3
import gzip,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
# Structural date diagnostics only. IDs come from legacy parser output, not from
# strategy performance. This shows why an otherwise valid legacy series is or is not
# eligible for same-series N-PORT pairing under the frozen ±45-day report-date gate.
IDS=[
'S000062095','S000006408','S000006409','S000006410','S000006411','S000006412','S000006413','S000006414','S000051152','S000006415','S000006416',
'S000004306','S000004307','S000004308','S000004309','S000004313','S000004314','S000004316','S000004317','S000004326','S000004339','S000004340','S000004359','S000004370','S000004372','S000004373','S000008880','S000008881','S000019356','S000022498','S000022500','S000031906',
'S000053943','S000053944','S000053945','S000053946','S000053947','S000053948','S000058146','S000058147','S000058148'
]
with gzip.open(P,'rt',encoding='utf-8') as f:d=json.load(f)
rows=d.get('snapshots') or d.get('filings') or []
out={}
for sid in IDS:
    rr=[x for x in rows if x.get('seriesId')==sid]
    out[sid]=[{'reportDate':x.get('reportDate'),'filingDate':x.get('filingDate'),'holdingCount':len(x.get('holdings',[]))} for x in sorted(rr,key=lambda x:(x.get('reportDate',''),x.get('filingDate','')))]
print(json.dumps(out,indent=2))
