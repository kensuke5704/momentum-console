#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'data/research/nq-npx-structural-mapping-2006.json'
OUT=ROOT/'data/research/structural-new-matches-country-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
ADR_RE=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)

def main():
 data=json.loads(MAP.read_text()); ids={}
 for d in data.get('details',[]):
  if d.get('matchMethod') not in {'STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'} or d.get('status')!='MATCHED_UNIQUE' or len(d.get('identities',[]))!=1: continue
  ident=d['identities'][0];k=(ident['ticker'],ident['securityId']);r=ids.get(k)
  if r is None:r={'ticker':ident['ticker'],'securityId':ident['securityId'],'issuer':d['description'],'asOfReportDate':d['reportDate'],'aggregateWeight':0.0,'occurrenceCount':0};ids[k]=r
  r['aggregateWeight']+=float(d.get('weight') or 0);r['occurrenceCount']+=1
  if d['reportDate']<r['asOfReportDate']:r['asOfReportDate']=d['reportDate'];r['issuer']=d['description']
 rows=[]
 for r in sorted(ids.values(),key=lambda x:(x['ticker'],x['securityId'])):
  sid=(r.get('securityId') or '').upper();
  if sid and sid[0].isalpha():o={**r,'classification':'NON_US','resolutionSource':'CINS_ALPHA_PREFIX'}
  elif ADR_RE.search(r.get('issuer') or ''):o={**r,'classification':'NON_US','resolutionSource':'EXPLICIT_ADR_GDR'}
  else:o=cur.resolve(r)
  rows.append(o);print('COUNTRY',json.dumps({k:o.get(k) for k in ['ticker','issuer','aggregateWeight','classification','resolutionSource','stateCode']}),flush=True);time.sleep(.08)
 counts={k:sum(1 for r in rows if r.get('classification')==k) for k in ['US','NON_US','UNKNOWN']};weights={k:sum(float(r.get('aggregateWeight') or 0) for r in rows if r.get('classification')==k) for k in counts}
 out={'purpose':'PIT country attribution for only the newly recovered deterministic structural identity matches. Same conservative country hierarchy; UNKNOWN preserved. No returns/ranks used.','uniqueIdentityCount':len(rows),'classificationCounts':counts,'classificationWeights':weights,'rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
