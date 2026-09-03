#!/usr/bin/env python3
from __future__ import annotations
import glob,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/country-full-coverage-raw-header-2006.json'

def main():
 base=json.loads(BASE.read_text());over={}
 for p in sorted(glob.glob(str(ROOT/'data/research/sec-raw-header-country-shard-*-2006.json'))):
  d=json.loads(Path(p).read_text())
  for r in d.get('results',[]):
   if r.get('classification') in {'US','NON_US'}:
    over[(r.get('ticker'),r.get('securityId'))]=r
 rows=[];new_id=0;new_occ=0;new_w=0.0
 for r in base['identityRows']:
  rr=dict(r);k=(r.get('ticker'),r.get('securityId'));o=over.get(k)
  if r.get('classification')=='UNKNOWN' and o:
   rr.update({x:o.get(x) for x in ['classification','stateCode','resolutionSource','sourceUrl','transport'] if o.get(x) is not None})
   new_id+=1;new_occ+=int(r.get('occurrenceCount') or 0);new_w+=float(r.get('aggregateWeight') or 0)
  rows.append(rr)
 def icount(cls):return sum(1 for r in rows if r.get('classification')==cls)
 def iweight(cls):return sum(float(r.get('aggregateWeight') or 0) for r in rows if r.get('classification')==cls)
 def hcount(cls):return sum(int(r.get('occurrenceCount') or 0) for r in rows if r.get('classification')==cls)
 counts={c:icount(c) for c in ['US','NON_US','UNKNOWN']};weights={c:iweight(c) for c in counts};hcounts={c:hcount(c) for c in counts}
 base_all=base['allEcHoldingClassificationCounts'];base_allw=base['allEcHoldingClassificationWeights']
 allc=dict(base_all);allw=dict(base_allw)
 # raw-header overlays only baseline mapped UNKNOWN holdings.
 allc['UNKNOWN']-=new_occ;allc['US']=base_all['US']+sum(int(r.get('occurrenceCount') or 0) for r in rows if r.get('resolutionSource')=='PIT_RAW_SEC_HEADER_NAME_VALIDATED' and r.get('classification')=='US');allc['NON_US']=base_all['NON_US']+sum(int(r.get('occurrenceCount') or 0) for r in rows if r.get('resolutionSource')=='PIT_RAW_SEC_HEADER_NAME_VALIDATED' and r.get('classification')=='NON_US')
 add_us=sum(float(r.get('aggregateWeight') or 0) for r in rows if r.get('resolutionSource')=='PIT_RAW_SEC_HEADER_NAME_VALIDATED' and r.get('classification')=='US');add_non=sum(float(r.get('aggregateWeight') or 0) for r in rows if r.get('resolutionSource')=='PIT_RAW_SEC_HEADER_NAME_VALIDATED' and r.get('classification')=='NON_US')
 allw['UNKNOWN']=base_allw['UNKNOWN']-add_us-add_non;allw['US']=base_allw['US']+add_us;allw['NON_US']=base_allw['NON_US']+add_non
 totalc=sum(allc.values());totalw=sum(allw.values())
 out={'year':2006,'purpose':'Merge validated raw historical SEC-header country classifications into the frozen UNKNOWN-only country baseline. Existing resolved labels are unchanged.','rawHeaderNewResolvedIdentityCount':new_id,'rawHeaderNewResolvedHoldingOccurrences':new_occ,'rawHeaderNewResolvedWeight':new_w,'identityClassificationCounts':counts,'identityClassificationWeights':weights,'mappedHoldingClassificationCounts':hcounts,'mappedHoldingClassificationWeights':weights,'allEcHoldingClassificationCounts':allc,'allEcHoldingClassificationWeights':allw,'allEcResolvedCountRate':(allc['US']+allc['NON_US'])/totalc,'allEcResolvedWeightRate':(allw['US']+allw['NON_US'])/totalw,'identityRows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='identityRows'}),flush=True)
if __name__=='__main__':main()
