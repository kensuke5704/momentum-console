#!/usr/bin/env python3
from __future__ import annotations
import json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/nq-npx-mapping-2006.json';MASTER=ROOT/'data/research/npx-security-master-2006.json';OUT=ROOT/'data/research/nq-npx-primary-shareclass-mapping-2006.json'
def strip_share_class(s:str)->str:
 return ' '.join(re.sub(r'\b(?:CLASS|CL)\s+[A-Z0-9]+\b',' ',str(s),flags=re.I).split())
def main():
 base=json.loads(BASE.read_text());master=json.loads(MASTER.read_text());idx=defaultdict(set)
 for r in master['records']:
  n=r.get('normalizedIssuer');t=r.get('ticker');sid=r.get('securityId')
  if n and t and sid:idx[n].add((t,sid))
 additions=[]
 for d in base['details']:
  if d.get('status')=='MATCHED_UNIQUE':continue
  ids=set();evidence=[]
  for a in d.get('normalizedAliases',[]):
   x=strip_share_class(a)
   if x==a:continue
   got=idx.get(x,set())
   if len(got)==1:
    ids.update(got);evidence.append({'sourceAlias':a,'shareClassStrippedAlias':x,'identity':{'ticker':next(iter(got))[0],'securityId':next(iter(got))[1]}})
  if len(ids)==1:
   t,sid=next(iter(ids));additions.append({'seriesId':d['seriesId'],'fundTickers':d.get('fundTickers',[]),'reportDate':d.get('reportDate'),'description':d['description'],'weight':d['weight'],'ticker':t,'securityId':sid,'method':'SHARE_CLASS_STRIPPED_UNIQUE_EXACT_ISSUER','evidence':evidence})
 base_count=int(base['uniqueMatchedCount']);base_weight=float(base['uniqueMatchedWeight']);den_count=int(base['eligibleHoldingCount']);den_weight=float(base['eligibleHoldingWeight']);add_weight=sum(float(x['weight']) for x in additions)
 out={'year':2006,'purpose':'Primary deterministic mapping extension preregistered for historical Gate B. Starting from baseline exact normalized issuer matches, remove only explicit share-class labels (Class X / Cl X) from legacy issuer aliases and accept only when the resulting N-PX normalized issuer maps to exactly one ticker/securityId identity. No long-prefix, fuzzy/edit-distance, country assumptions, ranks, or returns are used.','baselineMatchedCount':base_count,'baselineMatchedWeight':base_weight,'eligibleHoldingCount':den_count,'eligibleHoldingWeight':den_weight,'additionCount':len(additions),'additionWeight':add_weight,'primaryMatchedCount':base_count+len(additions),'primaryMatchedWeight':base_weight+add_weight,'primaryMatchedCountRate':(base_count+len(additions))/den_count,'primaryMatchedWeightRate':(base_weight+add_weight)/den_weight,'additions':additions}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='additions'}),flush=True)
if __name__=='__main__':main()
