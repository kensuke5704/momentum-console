#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,math,re,statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
LEGACY=ROOT/'data/research/production-jan2020-legacy-extract.json'
HISTORY=ROOT/'data/universe-history.json'
OUT=ROOT/'data/research/production-jan2020-hybrid-shadow.json'
ASOF='2020-01-28'; SIGNAL='2020-01'; GFIN_ACC='0001752724-20-013847'; GFIN_SID='S000063326'

STRUCTURED_OR_INCOME=re.compile(r'\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b',re.I)
BROAD=re.compile(r'\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b',re.I)

def norm(raw):
 s=(raw or '').upper().replace('&',' AND ')
 # Security-class language is not issuer identity and is removed structurally.
 s=re.sub(r'\bCLASS\s+[A-Z0-9]+\b',' ',s)
 s=re.sub(r'\b(?:VOTING|NON VOTING) SHARES?\b',' ',s)
 s=re.sub(r'\bSHARES?\b',' ',s)
 s=re.sub(r'\b(INCORPORATED|INCORPORATION)\b','INC',s)
 s=re.sub(r'\b(CORPORATION|CORPORA?TION)\b','CORP',s)
 s=re.sub(r'\bCOMPANY\b','CO',s);s=re.sub(r'\bLIMITED\b','LTD',s)
 s=re.sub(r'\bHLDGS\b','HOLDINGS',s);s=re.sub(r'\bPHARMACEUTICALS\b','PHARMACEUTICAL',s)
 return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def aliases(raw):
 n=norm(raw);out=[n] if n else []
 if n.startswith('THE '):out.append(n[4:])
 if n.endswith(' THE'):out.append(n[:-4])
 return list(dict.fromkeys(x for x in out if x))
def history_month(x):
 if isinstance(x,dict):
  if x.get('signalMonth')==SIGNAL:return x
  for v in x.values():
   r=history_month(v)
   if r:return r
 elif isinstance(x,list):
  for v in x:
   r=history_month(v)
   if r:return r
 return None

def identity_master(filings):
 by=defaultdict(lambda:defaultdict(set))
 for f in filings:
  if f.get('filingDate','')>ASOF:continue
  sid=f.get('seriesId','')
  for h in f.get('holdings',[]):
   sym=(h.get('symbol') or '').strip().upper();issuer=h.get('issuerName') or ''
   if not sym or not issuer:continue
   for a in aliases(issuer):by[a][sym].add(sid)
 return by
def resolve(master,sid,desc):
 for a in aliases(desc):
  cand=[]
  for sym,sids in master.get(a,{}).items():
   if any(x!=sid for x in sids):cand.append(sym)
  cand=sorted(set(cand))
  if len(cand)==1:return cand[0]
  if len(cand)>1:return ''
 return ''
def eligible(src):
 if STRUCTURED_OR_INCOME.search(src['seriesName']) or BROAD.search(src['seriesName']):return False
 hs=sorted([h for h in src['holdings'] if h['weight']>0],key=lambda h:-h['weight'])
 return 10<=len(hs)<=120 and sum(h['weight'] for h in hs)>=50 and sum(h['weight'] for h in hs[:10])>=25
def score(sources):
 rows={}
 for f in sources:
  rec=math.exp(-max(0,(date.fromisoformat(ASOF)-date.fromisoformat(f['filingDate'])).days)/120)
  for h in f['holdings']:
   w=h['weight'];sym=h['symbol']
   if not sym or w<=0:continue
   r=rows.setdefault(sym,{'seriesIds':set(),'aggregateWeight':0.0,'maxWeight':0.0,'recencyWeight':0.0})
   r['seriesIds'].add(f['seriesId']);r['aggregateWeight']+=w;r['maxWeight']=max(r['maxWeight'],w);r['recencyWeight']+=w*rec
 out=[]
 for sym,r in rows.items():
  ec=len(r['seriesIds'])
  if ec<2 and r['maxWeight']<4:continue
  sc=3*math.log1p(ec)+.5*math.log1p(r['aggregateWeight'])+.5*math.log1p(r['recencyWeight'])
  out.append({'symbol':sym,'etfCount':ec,'aggregateWeight':r['aggregateWeight'],'maxWeight':r['maxWeight'],'recencyWeight':r['recencyWeight'],'universeScore':sc})
 out.sort(key=lambda x:(-x['universeScore'],-x['etfCount'],-x['aggregateWeight'],x['symbol']))
 for i,x in enumerate(out[:80],1):x['universeRank']=i
 return out[:80]
def corr(x,y):
 if len(x)<2:return None
 mx=sum(x)/len(x);my=sum(y)/len(y);dx=[a-mx for a in x];dy=[b-my for b in y]
 den=math.sqrt(sum(a*a for a in dx)*sum(b*b for b in dy));return sum(a*b for a,b in zip(dx,dy))/den if den else None

def main():
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b
 master=identity_master(filings);legacy=json.loads(LEGACY.read_text())
 sources=[];mapping=[]
 for rec in legacy['records']:
  hs=[];mc=mw=tc=tw=0
  for h in rec['holdings']:
   tc+=1;tw+=h['weight'];sym=resolve(master,rec['seriesId'],h['description'])
   if sym:
    mc+=1;mw+=h['weight'];hs.append({'symbol':sym,'issuerName':h['description'],'weight':h['weight']})
  # Merge multiple share classes mapping to the same issuer symbol.
  merged={}
  for h in hs:
   r=merged.setdefault(h['symbol'],{'symbol':h['symbol'],'issuerName':h['issuerName'],'weight':0.0});r['weight']+=h['weight']
  src={'seriesId':rec['seriesId'],'seriesName':rec['seriesName'],'filingDate':rec['filingDate'],'reportDate':rec['reportDate'],'sourceKind':'LEGACY_RECONSTRUCTED','holdings':list(merged.values())}
  sources.append(src)
  mapping.append({'seriesId':rec['seriesId'],'legacyHoldings':tc,'mappedHoldings':mc,'mappedCountRate':mc/tc if tc else None,'mappedWeightRate':mw/tw if tw else None,'mappedWeight':mw,'eligibleAfterConservativeMapping':eligible(src),'mappedUniqueSymbols':len(merged)})
 # GFIN has no pre-NPORT same-series legacy report, so keep the exact contemporaneous NPORT source fixed.
 gf=next(f for f in filings if f.get('seriesId')==GFIN_SID and f.get('accession')==GFIN_ACC)
 sources.append({'seriesId':gf['seriesId'],'seriesName':gf['seriesName'],'filingDate':gf['filingDate'],'reportDate':gf['reportDate'],'sourceKind':'NPORT_FIXED_NO_LEGACY_PREDECESSOR','holdings':[{'symbol':h['symbol'],'issuerName':h.get('issuerName'),'weight':float(h['weight'])} for h in gf['holdings']]})
 kept=[s for s in sources if eligible(s)]
 shadow=score(kept)
 hist=history_month(json.loads(HISTORY.read_text()))
 if not hist:raise RuntimeError('Production 2020-01 history not found')
 prod=[x['symbol'] for x in hist['symbols']];cand=[x['symbol'] for x in shadow]
 common=set(prod)&set(cand);pr={s:i+1 for i,s in enumerate(prod)};cr={s:i+1 for i,s in enumerate(cand)}
 overlap=len(common)/len(prod);rho=corr([pr[s] for s in common],[cr[s] for s in common]);top2=prod[:2];hits=sum(s in set(cand) for s in top2)
 out={'purpose':'Evaluation-only January 2020 hybrid transition shadow. LRGE and PPTY are replaced by metadata-preregistered nearest legacy sources; GFIN remains exact N-PORT because no pre-NPORT same-series legacy report exists. Legacy tickers are accepted only from unique PIT cross-series issuer identity evidence in other already EC/US/CORP-filtered N-PORT filings. No Production holdings/ranks used to tune parsing or mapping.','asOf':ASOF,'productionUniverse':prod,'candidateUniverse':cand,'candidateRows':shadow,'sourceMapping':mapping,'sourceEligibility':[{'seriesId':s['seriesId'],'sourceKind':s['sourceKind'],'eligible':eligible(s),'holdingCount':len(s['holdings']),'holdingWeight':sum(h['weight'] for h in s['holdings']),'top10Weight':sum(sorted((h['weight'] for h in s['holdings']),reverse=True)[:10])} for s in sources],'metrics':{'topKOverlap':overlap,'commonNames':len(common),'spearmanCommonRanks':rho,'productionTop2':top2,'top2Hits':hits,'top2IndividualRetention':hits/len(top2)},'limitations':['GFIN cannot be legacy-substituted because no pre-NPORT same-series legacy report exists.','LRGE legacy report is 274 days older than its first NPORT report; PPTY is 91 days older.','This is a transition hybrid validation, not by itself a full historical Gate B pass.']}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('MAPPING',json.dumps(mapping),flush=True);print('ELIGIBILITY',json.dumps(out['sourceEligibility']),flush=True);print('CANDIDATE',json.dumps(cand),flush=True);print('METRICS',json.dumps(out['metrics']),flush=True)
if __name__=='__main__':main()
