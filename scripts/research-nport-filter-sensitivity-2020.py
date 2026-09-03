#!/usr/bin/env python3
from __future__ import annotations
import csv,json,math,re,sys,zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/nport-filter-sensitivity-2020.json'
HIST=ROOT/'data/universe-history.json'
ASOF='2020-02-29';MONTH='2020-02'
STRUCT=re.compile(r'\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b',re.I)
BROAD=re.compile(r'\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b',re.I)
VARIANTS={'EC':lambda r:r['ASSET_CAT']=='EC','EC_US':lambda r:r['ASSET_CAT']=='EC' and r['INVESTMENT_COUNTRY']=='US','EC_US_CORP':lambda r:r['ASSET_CAT']=='EC' and r['INVESTMENT_COUNTRY']=='US' and r['ISSUER_TYPE']=='CORP'}

def rows(z,table):
 with z.open(table+'.tsv') as fh:
  import io
  yield from csv.DictReader(io.TextIOWrapper(fh,encoding='utf-8-sig',errors='replace',newline=''),delimiter='\t')
def pdate(x):
 x=(x or '').strip()
 if re.match(r'^\d{1,2}-[A-Z]{3}-\d{4}$',x,re.I):
  return __import__('datetime').datetime.strptime(x,'%d-%b-%Y').date().isoformat()
 return x[:10]
def eligible(name,hs):
 if STRUCT.search(name) or BROAD.search(name):return False
 ws=sorted([h['weight'] for h in hs if h['weight']>0],reverse=True)
 return 10<=len(ws)<=120 and sum(ws)>=50 and sum(ws[:10])>=25
def load(paths):
 submissions={};funds={};holding_rows={};tickers={}
 for path in paths:
  with zipfile.ZipFile(path) as z:
   for r in rows(z,'SUBMISSION'):
    submissions[r['ACCESSION_NUMBER']]={'reportDate':pdate(r['REPORT_DATE']),'filingDate':pdate(r['FILING_DATE'])}
   for r in rows(z,'FUND_REPORTED_INFO'):
    a=r['ACCESSION_NUMBER'];s=submissions.get(a);name=(r.get('SERIES_NAME') or '').strip()
    if s and (re.search(r'(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED',name,re.I)):
     funds[a]={'accession':a,'seriesId':r.get('SERIES_ID',''),'seriesName':name,**s}
   wanted=set(funds)
   for r in rows(z,'FUND_REPORTED_HOLDING'):
    a=r['ACCESSION_NUMBER']
    if a not in wanted:continue
    hid=r['HOLDING_ID'];holding_rows[hid]={'accession':a,'ASSET_CAT':r.get('ASSET_CAT',''),'INVESTMENT_COUNTRY':r.get('INVESTMENT_COUNTRY',''),'ISSUER_TYPE':r.get('ISSUER_TYPE',''),'issuerName':r.get('ISSUER_NAME',''),'weight':float(r.get('PERCENTAGE') or 0)}
   for r in rows(z,'IDENTIFIERS'):
    hid=r['HOLDING_ID']
    if hid not in holding_rows:continue
    t=(r.get('IDENTIFIER_TICKER') or '').strip().upper()
    if re.match(r'^[A-Z][A-Z0-9.^=-]{0,14}$',t):tickers.setdefault(hid,t)
 return funds,holding_rows,tickers

def build(funds,holding_rows,tickers,pred):
 byacc=defaultdict(list)
 for hid,h in holding_rows.items():
  if pred(h) and hid in tickers and h['weight']>0:byacc[h['accession']].append({'symbol':tickers[hid],'issuerName':h['issuerName'],'weight':h['weight']})
 filings=[]
 for a,f in funds.items():
  hs=byacc.get(a,[])
  if f['seriesId'] and hs:filings.append({**f,'holdings':hs})
 latest={}
 for f in filings:
  if f['filingDate']>ASOF:continue
  c=latest.get(f['seriesId'])
  if c is None or (f['filingDate'],f['accession'])>(c['filingDate'],c['accession']):latest[f['seriesId']]=f
 sources=[f for f in latest.values() if eligible(f['seriesName'],f['holdings'])]
 agg={}
 for f in sources:
  age=max(0,(date.fromisoformat(ASOF)-date.fromisoformat(f['filingDate'])).days);rf=math.exp(-age/120)
  for h in f['holdings']:
   x=agg.setdefault(h['symbol'],{'series':set(),'aggregateWeight':0.0,'maxWeight':0.0,'recencyWeight':0.0})
   x['series'].add(f['seriesId']);x['aggregateWeight']+=h['weight'];x['maxWeight']=max(x['maxWeight'],h['weight']);x['recencyWeight']+=h['weight']*rf
 out=[]
 for sym,x in agg.items():
  n=len(x['series'])
  if n<2 and x['maxWeight']<4:continue
  score=3*math.log1p(n)+.5*math.log1p(x['aggregateWeight'])+.5*math.log1p(x['recencyWeight'])
  out.append({'symbol':sym,'etfCount':n,'aggregateWeight':x['aggregateWeight'],'score':score})
 out.sort(key=lambda r:(-r['score'],-r['etfCount'],-r['aggregateWeight'],r['symbol']))
 return sources,out[:80]
def overlap(a,b,k):return len(set(x['symbol'] for x in a[:k])&set(x['symbol'] for x in b[:k]))/k if k else None
def spear(a,b):
 ra={x['symbol']:i+1 for i,x in enumerate(a)};rb={x['symbol']:i+1 for i,x in enumerate(b)};common=set(ra)&set(rb);n=len(common)
 if n<2:return None
 d2=sum((ra[s]-rb[s])**2 for s in common)
 return 1-6*d2/(n*(n*n-1)) if n>1 else None

def main():
 funds,hrs,tickers=load(sys.argv[1:]);res={}
 for name,pred in VARIANTS.items():
  src,u=build(funds,hrs,tickers,pred);res[name]={'sourceFilings':len(src),'universeSize':len(u),'symbols':u}
 prod=res['EC_US_CORP']['symbols'];K=len(prod)
 for name in ('EC','EC_US'):
  u=res[name]['symbols'];res[name]['vsProduction']={'topKOverlap':overlap(u,prod,K),'productionTop2Retained':sum(1 for x in prod[:2] if x['symbol'] in {y['symbol'] for y in u[:K]})/max(1,min(2,len(prod))),'commonPositionalRankAgreement':spear(u[:K],prod)}
 hist=json.loads(HIST.read_text());records=hist if isinstance(hist,list) else hist.get('months',hist.get('records',[]));rec=next((x for x in records if x.get('signalMonth')==MONTH),None)
 stored=[x['symbol'] if isinstance(x,dict) else x for x in (rec.get('symbols',[]) if rec else [])];raw=[x['symbol'] for x in prod]
 parity={'storedSize':len(stored),'rawSize':len(raw),'exact':stored==raw,'overlapAtStoredK':len(set(stored)&set(raw[:len(stored)]))/len(stored) if stored else None,'stored':stored,'rawTop':raw[:len(stored)]}
 out={'purpose':'Raw N-PORT transition sensitivity for EC / US / CORP filters. No strategy returns used. Valid only if EC_US_CORP raw reconstruction matches stored Production history closely.','asOf':ASOF,'productionParity':parity,'variants':res}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('PARITY',json.dumps(parity));
 for k,v in res.items():print('VARIANT',k,json.dumps({x:y for x,y in v.items() if x!='symbols'}))
if __name__=='__main__':main()
# research rerun marker: 2026-09-03 Gate B source/filter audit
