#!/usr/bin/env python3
import gzip,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
with gzip.open(R/'data/sec-nport/bootstrap.json.gz','rt',encoding='utf-8') as f:b=json.load(f)
filings=b.get('snapshots',b) if isinstance(b,dict) else b
series={'S000057700','S000063326','S000061208'}
# exact accessions frozen from stored Production universe history
accessions={'0001752724-20-012434','0001752724-20-013847','0001145549-20-003103'}
rows=[]
for x in filings:
 if x.get('seriesId') in series and x.get('accession') in accessions:
  r={k:x.get(k) for k in ['accession','seriesId','seriesName','reportDate','filingDate']}
  r['holdings']=[{k:h.get(k) for k in ['symbol','issuerName','weight']} for h in x.get('holdings',[])]
  rows.append(r)
  print('FILING',json.dumps({**{k:r[k] for k in r if k!='holdings'},'holdingCount':len(r['holdings'])}),flush=True)
  for h in r['holdings']:print('HOLDING',json.dumps({'seriesId':r['seriesId'],**h}),flush=True)
out={'purpose':'Frozen evaluation-only ground truth for the exact three N-PORT filings used by Production 2020-01. Must not be used to tune legacy parser/source selection.','filings':rows}
p=R/'data/research/production-jan2020-groundtruth.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n')
