#!/usr/bin/env python3
from __future__ import annotations
import json,math
from collections import defaultdict
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'data/research/nq-npx-mapping-2006.json';ADD=ROOT/'data/research/nq-npx-primary-shareclass-mapping-2006.json';COUNTRY=ROOT/'data/research/country-full-coverage-canonical-merge-2006.json';ADD_COUNTRY=ROOT/'data/research/primary-shareclass-country-2006.json';PIT=ROOT/'data/research/nq-pit-ec-filtered-2006.json';OUT=ROOT/'data/research/country-ambiguity-universe-sensitivity-2006.json'
def k(t,s):return (str(t or '').upper(),str(s or ''))
def corr(a,b):
 n=len(a)
 if n<2:return None
 ma=sum(a)/n;mb=sum(b)/n;num=sum((x-ma)*(y-mb) for x,y in zip(a,b));den=(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))**.5
 return num/den if den else None
def main():
 base=json.loads(MAP.read_text());add=json.loads(ADD.read_text());country=json.loads(COUNTRY.read_text());ac=json.loads(ADD_COUNTRY.read_text());pit=json.loads(PIT.read_text())
 clook={k(r.get('ticker'),r.get('securityId')):r.get('classification','UNKNOWN') for r in country['identityRows']}
 for r in ac['rows']:
  if r.get('classification') in {'US','NON_US'}:clook[k(r.get('ticker'),r.get('securityId'))]=r['classification']
 filings={r['seriesId']:r for r in pit['records']};asof=max(r['filingDate'] for r in pit['records'])
 holdings={}
 for d in base['details']:
  if d.get('status')=='MATCHED_UNIQUE' and len(d.get('identities') or [])==1:
   i=d['identities'][0];holdings[(d['seriesId'],d['reportDate'],d['description'])]={'seriesId':d['seriesId'],'reportDate':d['reportDate'],'description':d['description'],'weight':float(d['weight']),'ticker':i['ticker'].upper(),'securityId':i['securityId'],'mappingMethod':'BASELINE_EXACT'}
 for a in add['additions']:
  holdings[(a['seriesId'],a['reportDate'],a['description'])]={'seriesId':a['seriesId'],'reportDate':a['reportDate'],'description':a['description'],'weight':float(a['weight']),'ticker':a['ticker'].upper(),'securityId':a['securityId'],'mappingMethod':a['method']}
 def build(case):
  by=defaultdict(list)
  for h in holdings.values():
   cls=clook.get(k(h['ticker'],h['securityId']),'UNKNOWN')
   if cls=='US' or (case=='UPPER_BOUND' and cls=='UNKNOWN'):by[h['seriesId']].append({**h,'countryClassification':cls})
  eligible={}
  for sid,hs in by.items():
   ws=sorted([h['weight'] for h in hs if h['weight']>0],reverse=True);cnt=len(ws);total=sum(ws);top10=sum(ws[:10])
   if 10<=cnt<=120 and total>=50 and top10>=25:eligible[sid]=hs
  rows={};ad=date.fromisoformat(asof)
  for sid,hs in eligible.items():
   fd=filings[sid]['filingDate'];age=max(0,(ad-date.fromisoformat(fd)).days);rf=math.exp(-age/120)
   for h in hs:
    sym=h['ticker'];r=rows.setdefault(sym,{'seriesIds':set(),'aggregateWeight':0.0,'maxWeight':0.0,'recencyWeight':0.0});r['seriesIds'].add(sid);r['aggregateWeight']+=h['weight'];r['maxWeight']=max(r['maxWeight'],h['weight']);r['recencyWeight']+=h['weight']*rf
  out=[]
  for sym,r in rows.items():
   n=len(r['seriesIds'])
   if n<2 and r['maxWeight']<4:continue
   score=3*math.log1p(n)+0.5*math.log1p(r['aggregateWeight'])+0.5*math.log1p(r['recencyWeight']);out.append({'symbol':sym,'etfCount':n,'aggregateWeight':r['aggregateWeight'],'maxWeight':r['maxWeight'],'recencyWeight':r['recencyWeight'],'universeScore':score})
  out.sort(key=lambda x:(-x['universeScore'],-x['etfCount'],-x['aggregateWeight'],x['symbol']))
  for i,r in enumerate(out[:80],1):r['universeRank']=i
  return {'case':case,'eligibleSeriesCount':len(eligible),'eligibleSeriesIds':sorted(eligible),'symbols':out[:80]}
 lower=build('LOWER_BOUND');upper=build('UPPER_BOUND');ls=[x['symbol'] for x in lower['symbols']];us=[x['symbol'] for x in upper['symbols']];K=min(len(ls),len(us));samek=len(set(ls[:K])&set(us[:K]))/K if K else None;rl={s:i+1 for i,s in enumerate(ls)};ru={s:i+1 for i,s in enumerate(us)};common=sorted(set(rl)&set(ru));rho=corr([rl[s] for s in common],[ru[s] for s in common]);top2=ls[:2]
 out={'year':2006,'purpose':'Preregistered country ambiguity sensitivity using primary deterministic identity mapping only. LOWER_BOUND retains only directly evidenced US identities. UPPER_BOUND additionally retains mapped UNKNOWN identities as US for sensitivity only; it is never promoted to primary. Series eligibility and Production breadth scoring are recomputed after country filtering. No returns, ranks from later periods, or strategy outcomes are used.','asOf':asof,'mappingPolicy':'BASELINE_EXACT_PLUS_SHARE_CLASS_STRIPPED_UNIQUE_EXACT','countryLowerPolicy':'DIRECT_PIT_US_ONLY','countryUpperPolicy':'DIRECT_PIT_US_PLUS_MAPPED_UNKNOWN_AS_US_SENSITIVITY_ONLY','lower':lower,'upper':upper,'comparison':{'comparisonK':K,'topKOverlap':samek,'commonSymbolCount':len(common),'commonRankSpearman':rho,'lowerTop2':top2,'lowerTop2RetainedInUpperTop2':sum(1 for s in top2 if s in us[:2]),'lowerTop2RetainedAnywhereInUpper':sum(1 for s in top2 if s in us)}}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({'asOf':asof,'lowerSize':len(ls),'upperSize':len(us),'lowerEligibleSeries':lower['eligibleSeriesCount'],'upperEligibleSeries':upper['eligibleSeriesCount'],**out['comparison']}),flush=True)
if __name__=='__main__':main()
