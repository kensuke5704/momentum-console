#!/usr/bin/env python3
from __future__ import annotations
import json,math,re
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
COUNTRY=ROOT/'data/research/country-final-structural-merge-2006.json'
OUT=ROOT/'data/research/country-uncertainty-universe-sensitivity-2006.json'
ASOF='2006-05-31'
STRUCTURED_OR_INCOME=re.compile(r'\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b',re.I)
BROAD=re.compile(r'\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b',re.I)
def days(a,b): return max(0,(date.fromisoformat(a)-date.fromisoformat(b)).days)
def rank(rows):
 return sorted(rows,key=lambda r:(-r['universeScore'],-r['etfCount'],-r['aggregateWeight'],r['symbol']))
def spearman(a,b):
 ra={r['symbol']:i+1 for i,r in enumerate(a)};rb={r['symbol']:i+1 for i,r in enumerate(b)};common=sorted(set(ra)&set(rb));n=len(common)
 if n<2:return None
 d2=sum((ra[x]-rb[x])**2 for x in common)
 return 1-6*d2/(n*(n*n-1))
def build(pit_records,crows,include_unknown):
 by_series={}
 for r in crows:
  if r.get('mappingStatus')!='MATCHED_UNIQUE' or len(r.get('identities') or [])!=1:continue
  cls=r.get('classification')
  if cls=='NON_US' or (cls=='UNKNOWN' and not include_unknown):continue
  sym=str(r['identities'][0].get('ticker') or '').upper().strip()
  if not sym:continue
  by_series.setdefault((r.get('seriesId'),r.get('reportDate')),[]).append({'symbol':sym,'weight':float(r.get('weight') or 0)})
 eligible=[]
 for f in pit_records:
  if f.get('filingDate','9999')>ASOF:continue
  name=f.get('seriesName') or ''
  if STRUCTURED_OR_INCOME.search(name) or BROAD.search(name):continue
  hs=sorted(by_series.get((f.get('seriesId'),f.get('reportDate')),[]),key=lambda x:-x['weight'])
  total=sum(x['weight'] for x in hs);top10=sum(x['weight'] for x in hs[:10])
  if not (10<=len(hs)<=120 and total>=50 and top10>=25):continue
  eligible.append({'seriesId':f['seriesId'],'seriesName':name,'filingDate':f['filingDate'],'holdings':hs,'holdingCount':len(hs),'totalWeight':total,'top10Weight':top10})
 rows={}
 for f in eligible:
  rec=math.exp(-days(ASOF,f['filingDate'])/120)
  for h in f['holdings']:
   r=rows.setdefault(h['symbol'],{'symbol':h['symbol'],'seriesIds':set(),'aggregateWeight':0.0,'maxWeight':0.0,'recencyWeight':0.0})
   r['seriesIds'].add(f['seriesId']);r['aggregateWeight']+=h['weight'];r['maxWeight']=max(r['maxWeight'],h['weight']);r['recencyWeight']+=h['weight']*rec
 out=[]
 for r in rows.values():
  etf=len(r['seriesIds'])
  if etf<2 and r['maxWeight']<4:continue
  out.append({'symbol':r['symbol'],'etfCount':etf,'aggregateWeight':r['aggregateWeight'],'maxWeight':r['maxWeight'],'recencyWeight':r['recencyWeight'],'universeScore':3*math.log1p(etf)+.5*math.log1p(r['aggregateWeight'])+.5*math.log1p(r['recencyWeight'])})
 return eligible,rank(out)
def main():
 pit=json.loads(PIT.read_text());country=json.loads(COUNTRY.read_text())
 lower_f,lower=build(pit['records'],country['rows'],False);upper_f,upper=build(pit['records'],country['rows'],True)
 metrics={}
 for k in (10,20,40,80):
  la=[r['symbol'] for r in lower[:k]];ua=[r['symbol'] for r in upper[:k]];den=min(k,len(la),len(ua));metrics[f'top{k}Overlap']=len(set(la)&set(ua))/den if den else None
 common=set(r['symbol'] for r in lower)&set(r['symbol'] for r in upper)
 metrics['commonSymbolCount']=len(common);metrics['spearmanAllCommon']=spearman(lower,upper);metrics['lowerTop2RetainedInUpperTop2']=len(set(r['symbol'] for r in lower[:2])&set(r['symbol'] for r in upper[:2]))/max(1,min(2,len(lower)))
 out={'year':2006,'asOf':ASOF,'purpose':'Country-uncertainty sensitivity only. LOWER includes only conservatively resolved US mapped holdings. UPPER additionally includes mapped UNKNOWN holdings but still excludes resolved NON_US. Each scenario independently recomputes Production ETF eligibility, 120-day recency, breadth score, and ranking. UPPER is sensitivity only and is not an accepted country rule. No returns used.','lower':{'eligibleSeriesCount':len(lower_f),'universeMemberCount':len(lower),'eligibleSeries':[{'seriesId':x['seriesId'],'holdingCount':x['holdingCount'],'totalWeight':x['totalWeight'],'top10Weight':x['top10Weight']} for x in lower_f],'top80':lower[:80]},'upper':{'eligibleSeriesCount':len(upper_f),'universeMemberCount':len(upper),'eligibleSeries':[{'seriesId':x['seriesId'],'holdingCount':x['holdingCount'],'totalWeight':x['totalWeight'],'top10Weight':x['top10Weight']} for x in upper_f],'top80':upper[:80]},'metrics':metrics}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({'lowerEligibleSeries':len(lower_f),'upperEligibleSeries':len(upper_f),'lowerMembers':len(lower),'upperMembers':len(upper),'metrics':metrics}),flush=True)
 print('LOWER_TOP20',json.dumps([r['symbol'] for r in lower[:20]]),flush=True);print('UPPER_TOP20',json.dumps([r['symbol'] for r in upper[:20]]),flush=True)
if __name__=='__main__':main()
