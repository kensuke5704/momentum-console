#!/usr/bin/env python3
from __future__ import annotations
import json, math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
MAP=ROOT/'data/research/nq-npx-structural-mapping-2006.json'
COUNTRY=ROOT/'data/research/country-full-coverage-raw-header-2006.json'
NEWC=ROOT/'data/research/structural-new-matches-country-2006.json'
OUT=ROOT/'data/research/country-uncertainty-universe-bounds-2006.json'
EXCL1=('2X','3X','ULTRA','BULL','BEAR','INVERSE','SHORT','COVERED CALL','OPTION INCOME','PREMIUM INCOME','BUFFER','DEFINED OUTCOME','BOND','FIXED INCOME','TREASURY','MUNICIPAL','INCOME','DIVIDEND','ALLOCATION')
EXCL2=('S&P 500','TOTAL MARKET','RUSSELL 1000','RUSSELL 2000','NASDAQ-100','NASDAQ 100','DOW JONES','LARGE CAP BLEND','MID CAP BLEND','SMALL CAP BLEND')
def age(asof, filed):
 try:return max(0,(datetime.fromisoformat(asof)-datetime.fromisoformat(filed)).days)
 except:return 0
def rho(a,b):
 common=sorted(set(a)&set(b))
 if len(common)<2:return None
 ra={s:i+1 for i,s in enumerate(a)};rb={s:i+1 for i,s in enumerate(b)};n=len(common);d=sum((ra[s]-rb[s])**2 for s in common)
 return 1-6*d/(n*(n*n-1))
def eligible(name, hs):
 u=(name or '').upper()
 if any(x in u for x in EXCL1+EXCL2):return False
 ws=sorted((h['weight'] for h in hs if h['weight']>0),reverse=True)
 return 10<=len(ws)<=120 and sum(ws)>=50 and sum(ws[:10])>=25
def build(mode, records, details, cls):
 asof=max((r.get('filingDate') or r.get('reportDate') for r in records))
 byseries=defaultdict(list)
 for d in details:
  if d.get('status')!='MATCHED_UNIQUE' or len(d.get('identities',[]))!=1:continue
  ident=d['identities'][0];c=cls.get((ident.get('ticker'),ident.get('securityId')),'UNKNOWN')
  keep=(c=='US') or (mode=='UPPER' and c=='UNKNOWN')
  if not keep:continue
  byseries[d['seriesId']].append({'symbol':ident['ticker'].upper(),'weight':float(d.get('weight') or 0),'country':c})
 sources=[]
 for r in records:
  hs=byseries.get(r.get('seriesId'),[])
  if eligible(r.get('seriesName'),hs):sources.append((r,hs))
 rows={}
 for r,hs in sources:
  filed=r.get('filingDate') or r.get('reportDate');rec=math.exp(-age(asof,filed)/120)
  for h in hs:
   z=rows.setdefault(h['symbol'],{'series':set(),'aggregateWeight':0.0,'maxWeight':0.0,'recencyWeight':0.0})
   z['series'].add(r['seriesId']);z['aggregateWeight']+=h['weight'];z['maxWeight']=max(z['maxWeight'],h['weight']);z['recencyWeight']+=h['weight']*rec
 ranked=[]
 for sym,z in rows.items():
  n=len(z['series'])
  if n<2 and z['maxWeight']<4:continue
  score=3*math.log1p(n)+.5*math.log1p(z['aggregateWeight'])+.5*math.log1p(z['recencyWeight'])
  ranked.append({'symbol':sym,'etfCount':n,'aggregateWeight':z['aggregateWeight'],'maxWeight':z['maxWeight'],'recencyWeight':z['recencyWeight'],'universeScore':score})
 ranked.sort(key=lambda x:(-x['universeScore'],-x['etfCount'],-x['aggregateWeight'],x['symbol']))
 for i,x in enumerate(ranked[:80],1):x['rank']=i
 return {'mode':mode,'asOf':asof,'eligibleSeriesCount':len(sources),'eligibleSeriesIds':[r['seriesId'] for r,_ in sources],'ranking':ranked[:80]}
def main():
 pit=json.loads(PIT.read_text());mp=json.loads(MAP.read_text());co=json.loads(COUNTRY.read_text());nc=json.loads(NEWC.read_text())
 cls={}
 for r in co.get('identityRows',[]):cls[(r.get('ticker'),r.get('securityId'))]=r.get('classification','UNKNOWN')
 for r in nc.get('rows',[]):
  k=(r.get('ticker'),r.get('securityId'))
  if cls.get(k,'UNKNOWN')=='UNKNOWN' and r.get('classification') in {'US','NON_US'}:cls[k]=r['classification']
 strict=build('STRICT',pit['records'],mp['details'],cls);upper=build('UPPER',pit['records'],mp['details'],cls)
 a=[x['symbol'] for x in strict['ranking']];b=[x['symbol'] for x in upper['ranking']];k=min(len(a),len(b),80);common=set(a[:k])&set(b[:k])
 top2=set(a[:2]);top2ret=len(top2&set(b[:2]))/len(top2) if top2 else None
 out={'purpose':'Country-uncertainty bound diagnostic using latest raw-historical-header country evidence. STRICT excludes UNKNOWN; UPPER includes UNKNOWN only as a sensitivity upper bound. NON_US is excluded in both. UPPER is never an operational US inference. Same structural mapping and Production breadth-score/eligibility mechanics are used; no return data.','strict':strict,'upper':upper,'comparison':{'K':k,'topKOverlapCount':len(common),'topKOverlapRate':len(common)/k if k else None,'commonNameSpearman':rho(a[:k],b[:k]),'strictTop2RetainedInUpperTop2':top2ret,'strictTop10Overlap':len(set(a[:10])&set(b[:10]))/min(10,len(a),len(b)) if min(len(a),len(b)) else None}}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({'strictEligibleSeries':strict['eligibleSeriesCount'],'upperEligibleSeries':upper['eligibleSeriesCount'],**out['comparison']}),flush=True);print('STRICT_TOP20',json.dumps(a[:20]),flush=True);print('UPPER_TOP20',json.dumps(b[:20]),flush=True)
if __name__=='__main__':main()
