#!/usr/bin/env python3
import gzip,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
# S000012478 = First Trust NYSE Arca Biotechnology Index Fund (FBT),
# independently confirmed from SEC N-CEN. Existing SPDR IDs retained as controls.
IDS=['S000012478','S000062095','S000006409','S000006410','S000006411','S000006412']
with gzip.open(P,'rt',encoding='utf-8') as f:d=json.load(f)
rows=d.get('snapshots') or d.get('filings') or []
out={}
for sid in IDS:
    rr=[x for x in rows if x.get('seriesId')==sid]
    out[sid]=[{'reportDate':x.get('reportDate'),'filingDate':x.get('filingDate'),'holdingCount':len(x.get('holdings',[]))} for x in sorted(rr,key=lambda x:(x.get('reportDate',''),x.get('filingDate','')))]
print(json.dumps(out,indent=2))
