#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
SM=ROOT/'data/research/nq-npx-structural-mapping-2006.json'
BASE=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
SNEW=ROOT/'data/research/structural-new-matches-country-2006.json'
OUT=ROOT/'data/research/country-final-structural-merge-2006.json'
ADR_RE=re.compile(r'\b(?:ADR|GDR|ADS|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY|DEPOSITARY RECEIPT)\b',re.I)

def key(r): return (str(r.get('ticker') or '').upper(),str(r.get('securityId') or '').upper())
def main():
 sm=json.loads(SM.read_text());base=json.loads(BASE.read_text());snew=json.loads(SNEW.read_text())
 cmap={key(r):r.get('classification','UNKNOWN') for r in base.get('identityRows',[]) if key(r)!=("","")}
 source={key(r):r.get('resolutionSource') for r in base.get('identityRows',[]) if key(r)!=("","")}
 # Overlay only additional resolved filing-index classifications on prior UNKNOWN.
 for p in sorted((ROOT/'data/research').glob('sec-filing-index-country-shard-*-2006.json')):
  obj=json.loads(p.read_text())
  for r in obj.get('rows',[]):
   k=key(r);c=r.get('classification','UNKNOWN')
   if k!=("","") and c in {'US','NON_US'} and cmap.get(k,'UNKNOWN')=='UNKNOWN':
    cmap[k]=c;source[k]=r.get('resolutionSource') or 'PIT_FILING_INDEX'
 # Add newly recovered structural identities not represented in old mapping.
 for r in snew.get('rows',[]):
  k=key(r);c=r.get('classification','UNKNOWN')
  if k!=("","") and k not in cmap:
   cmap[k]=c;source[k]=r.get('resolutionSource')
 rows=[];counts=Counter();weights=defaultdict(float);methods=Counter()
 for d in sm.get('details',[]):
  w=float(d.get('weight') or 0);cls='UNKNOWN';method='UNRESOLVED'
  ids=d.get('identities') or []
  if d.get('status')=='MATCHED_UNIQUE' and len(ids)==1:
   k=key(ids[0]);cls=cmap.get(k,'UNKNOWN')
   if cls!='UNKNOWN':method=source.get(k) or 'IDENTITY_COUNTRY'
  # Explicit depositary evidence is a conservative non-US fallback only if still unknown.
  if cls=='UNKNOWN' and ADR_RE.search(str(d.get('description') or '')):
   cls='NON_US';method='EXPLICIT_ADR_GDR'
  counts[cls]+=1;weights[cls]+=w;methods[method]+=1
  rows.append({'seriesId':d.get('seriesId'),'reportDate':d.get('reportDate'),'description':d.get('description'),'weight':w,'mappingStatus':d.get('status'),'identities':ids,'classification':cls,'classificationSource':method})
 total_count=len(rows);total_weight=sum(weights.values());resolved_count=counts['US']+counts['NON_US'];resolved_weight=weights['US']+weights['NON_US']
 out={'year':2006,'purpose':'Holding-level conservative merge for the 936 EC holdings after deterministic structural identity mapping. Existing country classifications are frozen; historical filing-index results may promote prior UNKNOWN only; newly recovered structural identities use the same conservative country evidence; remaining explicit ADR/GDR is NON_US; all other unresolved holdings remain UNKNOWN. No current state, universe ranks, or returns used.','totalHoldingCount':total_count,'totalHoldingWeight':total_weight,'classificationCounts':dict(counts),'classificationWeights':dict(weights),'resolvedCount':resolved_count,'resolvedWeight':resolved_weight,'resolvedCountRate':resolved_count/total_count if total_count else None,'resolvedWeightRate':resolved_weight/total_weight if total_weight else None,'classificationSources':dict(methods),'rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
