#!/usr/bin/env python3
from __future__ import annotations

import json, math, re, statistics
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/nq-hybrid-country-pit-h1-2006.json'
GATEB=ROOT/'data/research/nq-hybrid-gate-b-h1-2006.json'
OUT=ROOT/'data/research/nq-hybrid-mapping-extreme-sensitivity-h1-2006.json'

STRUCTURED=re.compile(r'\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b',re.I)
BROAD=re.compile(r'\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b',re.I)
NONCORP=[re.compile(x,re.I) for x in [r'\b(?:ETF|EXCHANGE[ -]TRADED|MUTUAL FUND|INDEX FUND|INVESTMENT FUND|INCOME FUND|EQUITY FUND|MONEY MARKET FUND)\b',r'\b(?:HEDGE FUND|PRIVATE EQUITY FUND|VENTURE FUND)\b',r'\b(?:UNITED STATES TREASURY|U\.S\. TREASURY|GOVERNMENT OF|REPUBLIC OF|KINGDOM OF)\b',r'\b(?:CITY OF|COUNTY OF|MUNICIPAL)\b']]

def noncorp(x): return any(p.search(str(x or '')) for p in NONCORP)
def norm(raw):
 s=str(raw or '').upper().replace('&',' AND ')
 s=re.sub(r'\b(INCORPORATED|INCORPORATION)\b','INC',s); s=re.sub(r'\b(CORPORATION|CORPORA?TION)\b','CORP',s); s=re.sub(r'\bCOMPANY\b','CO',s); s=re.sub(r'\bLIMITED\b','LTD',s); s=re.sub(r'\bHLDGS\b','HOLDINGS',s); s=re.sub(r'\bPHARMACEUTICALS\b','PHARMACEUTICAL',s)
 return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def cleaned(raw):
 s=str(raw or '')
 pats=[r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',r'\s*/[A-Z]{2}\s*$']
 changed=True
 while changed:
  changed=False
  for p in pats:
   ns=re.sub(p,'',s,flags=re.I).strip()
   if ns!=s: s=ns; changed=True
 return norm(s)
def eligible_opt(f):
 name=f.get('seriesName') or ''
 if STRUCTURED.search(name) or BROAD.search(name): return False
 hs=[]
 for h in f.get('holdings',[]):
  if h.get('legacyAssetSection')!='COMMON_EQUITY' or float(h.get('weight') or 0)<=0 or noncorp(h.get('description')): continue
  if h.get('mappingStatus')=='MATCHED_UNIQUE' and h.get('countryClassification')=='NON_US': continue
  hs.append(h)
 hs.sort(key=lambda h:float(h.get('weight') or 0),reverse=True)
 return 10<=len(hs)<=120 and sum(float(h.get('weight') or 0) for h in hs)>=50 and sum(float(h.get('weight') or 0) for h in hs[:10])>=25
def score(r):
 n=len(r['sources'])
 if not(n>=2 or r['maxWeight']>=4): return None
 return 3*math.log1p(n)+.5*math.log1p(r['aggregateWeight'])+.5*math.log1p(r['recencyWeight'])
def add(r,cid,w,rf):
 r['sources'].add(cid); r['aggregateWeight']+=w; r['recencyWeight']+=w*rf; r['maxWeight']=max(r['maxWeight'],w)
def corr(a,b):
 common=set(a)&set(b); n=len(common)
 if n<2:return None
 ra={x:i+1 for i,x in enumerate(a)}; rb={x:i+1 for i,x in enumerate(b)}; xa=[ra[x] for x in common]; xb=[rb[x] for x in common]; ma=sum(xa)/n; mb=sum(xb)/n; num=sum((x-ma)*(y-mb) for x,y in zip(xa,xb)); da=sum((x-ma)**2 for x in xa); db=sum((y-mb)**2 for y in xb)
 return num/math.sqrt(da*db) if da and db else None

def build_extreme(s,clean):
 asof=date.fromisoformat(s['asOf']); mapped={}; anon={}
 for f in s['sourceFilings']:
  if not eligible_opt(f):continue
  cid=f.get('canonicalIdentity'); rf=math.exp(-max(0,(asof-date.fromisoformat(f['filingDate'])).days)/120)
  for h in f.get('holdings',[]):
   if h.get('legacyAssetSection')!='COMMON_EQUITY' or float(h.get('weight') or 0)<=0 or noncorp(h.get('description')):continue
   w=float(h['weight'])
   if h.get('mappingStatus')=='MATCHED_UNIQUE':
    if h.get('countryClassification')=='NON_US':continue
    t=h.get('mappedTicker')
    if not t:continue
    add(mapped.setdefault(t,{'sources':set(),'aggregateWeight':0.,'recencyWeight':0.,'maxWeight':0.}),cid,w,rf)
   else:
    k=(cleaned if clean else norm)(h.get('description'))
    if k:add(anon.setdefault(k,{'sources':set(),'aggregateWeight':0.,'recencyWeight':0.,'maxWeight':0.}),cid,w,rf)
 ranked=[]
 for k,r in mapped.items():
  sc=score(r)
  if sc is not None:ranked.append((sc,k,False))
 for k,r in anon.items():
  sc=score(r)
  if sc is not None:ranked.append((sc,'__UNRESOLVED__:'+k,True))
 ranked.sort(key=lambda x:(-x[0],x[1])); return ranked[:80]

def main():
 c=json.loads(COUNTRY.read_text()); g=json.loads(GATEB.read_text()); modes={}
 for clean in (False,True):
  rows=[]
  for s,gs in zip(c['monthSnapshots'],g['monthSnapshots']):
   primary=[x['symbol'] for x in gs['primarySymbols']]; ranked=build_extreme(s,clean); extreme=[x[1] for x in ranked]; k=min(len(primary),len(extreme),80); p=primary[:k]; e=extreme[:k]; common=set(p)&set(e); overlap=len(common)/k if k else None; sp=corr(p,e); top2=primary[:2]
   rows.append({'signalMonth':s['signalMonth'],'topK':k,'overlap':overlap,'commonNameSpearman':sp,'top2IndividualRetention':sum(x in e for x in top2)/2 if len(top2)==2 else None,'top2BothRetained':all(x in e for x in top2) if len(top2)==2 else None,'anonymousTop80Count':sum(x[2] for x in ranked),'extremeSymbols':[x[1] for x in ranked]})
  ovs=[x['overlap'] for x in rows]; sps=[x['commonNameSpearman'] for x in rows if x['commonNameSpearman'] is not None]
  agg={'medianTopKOverlap':statistics.median(ovs),'minimumTopKOverlap':min(ovs),'medianSpearman':statistics.median(sps),'top2IndividualRetention':sum(x['top2IndividualRetention'] for x in rows)/len(rows),'top2BothMonthlyRetention':sum(bool(x['top2BothRetained']) for x in rows)/len(rows)}
  agg['pass']=agg['medianTopKOverlap']>=.80 and agg['minimumTopKOverlap']>=.70 and agg['medianSpearman']>=.75 and agg['top2IndividualRetention']>=.80 and agg['top2BothMonthlyRetention']>=.70
  modes['cleanedExact' if clean else 'rawNormalizedExact']={'months':rows,'aggregate':agg}
 out={'purpose':'Deliberately conservative assignment-free mapping residual sensitivity. Every unresolved positive COMMON_EQUITY row is assumed US/CORP; source eligibility uses that optimistic assumption; unresolved rows are grouped only by exact frozen issuer normalization and treated as entirely new anonymous securities rather than guessed tickers. This overstates disruption because an unresolved issuer may actually duplicate an already mapped security. No fuzzy assignment, returns, ranks, or strategy outcomes are used to identify securities.','catalogSha256':g['catalogSha256'],'thresholds':g['gateAEquivalentPracticalThresholds'],'modes':modes,'pass':all(x['aggregate']['pass'] for x in modes.values())}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps({k:v['aggregate'] for k,v in modes.items()},indent=2)); print('PASS',out['pass'])
if __name__=='__main__':main()
