#!/usr/bin/env python3
from __future__ import annotations
import glob,json,re
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data/research'
SM=D/'nq-npx-structural-mapping-2006.json'
BASE=D/'country-full-coverage-unknown-retry-2006.json'
SNEW=D/'structural-new-matches-country-2006.json'
OUT=D/'country-final-structural-merge-2006.json'
ADR_RE=re.compile(r'\b(?:ADR|GDR|ADS|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY|DEPOSITARY RECEIPT)\b',re.I)
ROUTE_GLOBS=['sec-filing-index-country-shard-*-2006.json','sec-hdr-country-shard-*-2006.json']

def key(r): return (str(r.get('ticker') or '').upper(),str(r.get('securityId') or '').upper())
def main():
 sm=json.loads(SM.read_text());base=json.loads(BASE.read_text());snew=json.loads(SNEW.read_text())
 frozen={key(r):r.get('classification','UNKNOWN') for r in base.get('identityRows',[]) if key(r)!=("","")}
 source={key(r):r.get('resolutionSource') for r in base.get('identityRows',[]) if key(r)!=("","")}
 evidence=defaultdict(list);route_files=[]
 for pat in ROUTE_GLOBS:
  for pstr in glob.glob(str(D/pat)):
   p=Path(pstr);route_files.append(p.name);obj=json.loads(p.read_text())
   for r in obj.get('rows',[]):
    k=key(r);c=r.get('classification','UNKNOWN')
    if k!=("","") and c in {'US','NON_US'}:
     evidence[k].append({'classification':c,'source':r.get('resolutionSource') or p.name,'stateCode':r.get('stateCode')})
 conflicts=[];cmap=dict(frozen)
 for k,ev in evidence.items():
  vals={e['classification'] for e in ev};old=cmap.get(k,'UNKNOWN')
  if old in {'US','NON_US'}:
   if any(v!=old for v in vals): conflicts.append({'ticker':k[0],'securityId':k[1],'frozen':old,'evidence':ev})
   continue
  if len(vals)==1:
   cmap[k]=next(iter(vals));source[k]='MULTIROUTE_PIT_COUNTRY' if len(ev)>1 else ev[0]['source']
  elif len(vals)>1:
   cmap[k]='CONFLICT';source[k]='CONFLICT';conflicts.append({'ticker':k[0],'securityId':k[1],'frozen':'UNKNOWN','evidence':ev})
 for r in snew.get('rows',[]):
  k=key(r);c=r.get('classification','UNKNOWN')
  if k==("",""): continue
  if k not in cmap:
   cmap[k]=c;source[k]=r.get('resolutionSource')
  elif cmap[k]=='UNKNOWN' and c in {'US','NON_US'}:
   cmap[k]=c;source[k]=r.get('resolutionSource')
 rows=[];counts=Counter();weights=defaultdict(float);methods=Counter()
 for d in sm.get('details',[]):
  w=float(d.get('weight') or 0);cls='UNKNOWN';method='UNRESOLVED';ids=d.get('identities') or []
  if d.get('status')=='MATCHED_UNIQUE' and len(ids)==1:
   k=key(ids[0]);cls=cmap.get(k,'UNKNOWN')
   if cls=='CONFLICT': cls='UNKNOWN';method='CONFLICT_UNRESOLVED'
   elif cls!='UNKNOWN': method=source.get(k) or 'IDENTITY_COUNTRY'
  if cls=='UNKNOWN' and method!='CONFLICT_UNRESOLVED' and ADR_RE.search(str(d.get('description') or '')):
   cls='NON_US';method='EXPLICIT_ADR_GDR'
  counts[cls]+=1;weights[cls]+=w;methods[method]+=1
  rows.append({'seriesId':d.get('seriesId'),'reportDate':d.get('reportDate'),'description':d.get('description'),'weight':w,'mappingStatus':d.get('status'),'identities':ids,'classification':cls,'classificationSource':method})
 total_count=len(rows);total_weight=sum(weights.values());resolved_count=counts['US']+counts['NON_US'];resolved_weight=weights['US']+weights['NON_US']
 out={'year':2006,'purpose':'Holding-level conservative final merge for EC holdings after deterministic structural identity mapping. Existing resolved country classifications are frozen; preregistered historical SEC filing-index and header-SGML routes may promote prior UNKNOWN only when their resolved classifications agree; conflicts remain unresolved. Newly recovered deterministic structural identities use the same conservative country evidence. Explicit ADR/GDR is NON_US fallback only when still unresolved. No current state, universe ranks, or returns used.','inputRouteFiles':sorted(route_files),'conflictCount':len(conflicts),'conflicts':conflicts,'totalHoldingCount':total_count,'totalHoldingWeight':total_weight,'classificationCounts':dict(counts),'classificationWeights':dict(weights),'resolvedCount':resolved_count,'resolvedWeight':resolved_weight,'resolvedCountRate':resolved_count/total_count if total_count else None,'resolvedWeightRate':resolved_weight/total_weight if total_weight else None,'classificationSources':dict(methods),'rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('rows','conflicts')}),flush=True)
if __name__=='__main__':main()
