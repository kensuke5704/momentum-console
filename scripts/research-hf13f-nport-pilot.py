#!/usr/bin/env python3
"""Free long-history universe proxy pilot using the public HF 13F mirror.

Pilot scope: 2022Q1-2023Q4. It downloads only shards 10-11 (~1 GB), filters
13F managers to concentrated portfolios analogous to production N-PORT ETF
eligibility, builds the same breadth score, maps PERMCO to ticker by an
independent raw-price fingerprint, and compares latest-public-quarter Top80
against the frozen N-PORT Top80. Research only; no production files changed.
"""
from __future__ import annotations
import json, math, os, statistics, time, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import pyarrow as pa
import pyarrow.ipc as ipc

ROOT=Path(__file__).resolve().parents[1]
BASE='https://huggingface.co/datasets/kurry/institutional-holdings-13f-quarterly/resolve/main/holdings'
UA='Mozilla/5.0 MomentumConsoleResearch/1.0'
SHARDS=[10,11]
CACHE=Path('/tmp/hf13f-pilot'); CACHE.mkdir(exist_ok=True)
OUT=ROOT/'data/research/hf13f-nport-pilot.json'
TOPN=80
PILOT_START='2022-05'; PILOT_END='2023-12'

def download(name):
 p=CACHE/name
 if p.exists(): return p
 print('DOWNLOAD',name,flush=True); r=urllib.request.Request(f'{BASE}/{name}',headers={'User-Agent':UA})
 with urllib.request.urlopen(r,timeout=300) as src,open(p,'wb') as dst:
  while True:
   b=src.read(8*1024*1024)
   if not b:break
   dst.write(b)
 print('DOWNLOADED',name,p.stat().st_size,flush=True); return p

def quarter_key(dt): return f'{dt.year}Q{(dt.month-1)//3+1}'
def qend(q):
 y=int(q[:4]); n=int(q[-1]); m=n*3
 import calendar
 return date(y,m,calendar.monthrange(y,m)[1])
def available_date(q): return qend(q)+timedelta(days=45) # conservative statutory maximum lag

def load_rows():
 # q -> manager -> list[(permco,dollar,price)]
 qs=defaultdict(lambda:defaultdict(list)); price_by=defaultdict(dict)
 for idx in SHARDS:
  name=f'data-{idx:05d}-of-00012.arrow'; p=download(name)
  with pa.memory_map(str(p),'r') as src:
   rd=ipc.open_stream(src)
   for batch in rd:
    names=batch.schema.names; cols={n:batch.column(names.index(n)) for n in ['mgrno','permco','fdate','price','dollar_holding']}
    for mgr,perm,fd,pr,val in zip(cols['mgrno'].to_pylist(),cols['permco'].to_pylist(),cols['fdate'].to_pylist(),cols['price'].to_pylist(),cols['dollar_holding'].to_pylist()):
     if fd is None or perm is None or mgr is None or val is None or val<=0:continue
     q=quarter_key(fd)
     if q<'2022Q1' or q>'2023Q4':continue
     pval=abs(float(pr)) if pr is not None else 0.0
     qs[q][str(mgr)].append((str(perm),float(val),pval))
     if pval>0: price_by[str(perm)][q]=pval
  os.remove(p)
 return qs,price_by

def concentrated_managers(managers):
 out={}
 for mgr,rows in managers.items():
  by=defaultdict(float)
  for perm,val,pr in rows:by[perm]+=val
  n=len(by); total=sum(by.values())
  if total<=0 or n<10 or n>120:continue
  top10=sum(sorted(by.values(),reverse=True)[:10])/total*100
  if top10<25:continue
  out[mgr]=(by,total,top10)
 return out

def score_quarter(managers):
 elig=concentrated_managers(managers); agg=defaultdict(lambda:{'mgrs':set(),'agg':0.,'max':0.})
 for mgr,(by,total,_) in elig.items():
  for perm,val in by.items():
   w=100*val/total; a=agg[perm];a['mgrs'].add(mgr);a['agg']+=w;a['max']=max(a['max'],w)
 ranks=[]
 for perm,a in agg.items():
  cnt=len(a['mgrs'])
  if cnt<2 and a['max']<4:continue
  # all records in a quarter share the same reporting age, so recency is monotone in aggregate weight
  score=3*math.log1p(cnt)+.5*math.log1p(a['agg'])+.5*math.log1p(a['agg'])
  ranks.append({'permco':perm,'managerCount':cnt,'aggregateWeight':a['agg'],'maxWeight':a['max'],'score':score})
 ranks.sort(key=lambda x:(-x['score'],-x['managerCount'],-x['aggregateWeight'],x['permco']))
 return ranks, len(elig)

def yahoo_raw(symbol):
 # Raw close is used only as an identifier bridge, not as a return input.
 s=symbol.replace('.','-'); p1=int(datetime(2021,12,1).timestamp());p2=int(datetime(2024,2,1).timestamp())
 for host in ['query1.finance.yahoo.com','query2.finance.yahoo.com']:
  url=f'https://{host}/v8/finance/chart/{s}?period1={p1}&period2={p2}&interval=1d&events=history'
  try:
   r=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
   with urllib.request.urlopen(r,timeout=25) as x:o=json.load(x)
   rr=o.get('chart',{}).get('result',[None])[0]
   if not rr:continue
   ts=rr.get('timestamp') or []; closes=((rr.get('indicators') or {}).get('quote') or [{}])[0].get('close') or []
   return [(date.fromtimestamp(t),c) for t,c in zip(ts,closes) if c and c>0]
  except Exception:pass
 return []
def nearest_close(rows,d):
 xs=[(dt,p) for dt,p in rows if dt<=d]
 return xs[-1][1] if xs else None

def build_mapping(price_by,symbols):
 quarters=['2022Q1','2022Q2','2022Q3','2022Q4','2023Q1','2023Q2','2023Q3','2023Q4']
 # Index candidates by approximate latest price to avoid all-pairs work.
 mapped={}; details={}
 for si,sym in enumerate(sorted(symbols),1):
  yr=yahoo_raw(sym)
  obs={q:nearest_close(yr,qend(q)) for q in quarters}; obs={q:p for q,p in obs.items() if p}
  best=[]
  if len(obs)>=4:
   for perm,pp in price_by.items():
    common=[q for q in obs if q in pp and pp[q]>0]
    if len(common)<4:continue
    # Raw CRSP-like price and Yahoo raw close should be nearly identical. Median relative
    # level error is an identity criterion independent of N-PORT overlap outcome.
    errs=[abs(pp[q]-obs[q])/max(pp[q],obs[q]) for q in common]
    med=statistics.median(errs); mx=max(errs)
    if med<=0.02:
     best.append((med,mx,-len(common),perm))
  best.sort(); accepted=None
  if best:
   # Require strong identity and separation when runner-up exists.
   b=best[0]; second=best[1] if len(best)>1 else None
   if b[0]<=0.01 and (second is None or second[0]>=max(0.015,b[0]*2)):
    accepted=b[3]
  if accepted:
   mapped[accepted]=sym
  details[sym]={'permco':accepted,'bestMedianRelativeError':best[0][0] if best else None,'runnerUpError':best[1][0] if len(best)>1 else None,'points':-best[0][2] if best else 0}
  if si%25==0:print('MAPPING',si,'/',len(symbols),'accepted',sum(1 for x in details.values() if x['permco']),flush=True)
  time.sleep(.02)
 return mapped,details

def main():
 qs,prices=load_rows(); print('QUARTERS',{q:sum(len(v) for v in m.values()) for q,m in qs.items()},flush=True)
 scored={}; eligible_counts={}
 for q,m in sorted(qs.items()):
  scored[q],eligible_counts[q]=score_quarter(m); print('SCORE',q,'eligibleManagers',eligible_counts[q],'assets',len(scored[q]),flush=True)
 hist=(json.loads((ROOT/'data/universe-history.json').read_text()).get('history') or [])
 months=[x for x in hist if PILOT_START<=x['signalMonth']<=PILOT_END]
 symbols={s['symbol'] for x in months for s in x.get('symbols',[])[:TOPN]}
 perm_to_sym,map_details=build_mapping(prices,symbols); print('MAPPED',len(perm_to_sym),'symbols from targets',len(symbols),flush=True)
 results=[]
 for x in months:
  asof=date.fromisoformat(x['asOf']); available=[q for q in scored if available_date(q)<=asof]
  if not available:continue
  q=max(available,key=qend); top=scored[q][:TOPN]; mapped=[perm_to_sym[r['permco']] for r in top if r['permco'] in perm_to_sym]
  target=[s['symbol'] for s in x.get('symbols',[])[:TOPN]]; a,b=set(mapped),set(target); inter=len(a&b)
  results.append({'month':x['signalMonth'],'asOf':x['asOf'],'sourceQuarter':q,'sourceAvailableDate':available_date(q).isoformat(),'mapped13fTop80':len(mapped),'mappingCoverageTop80':len(mapped)/TOPN,'intersection':inter,'overlapVsNport':inter/len(b) if b else None,'jaccardOnMapped':inter/len(a|b) if a|b else None,'13fSymbols':mapped,'nportSymbols':target})
  print('OVERLAP',x['signalMonth'],q,'mapped',len(mapped),'inter',inter,'/',len(target),flush=True)
 cov=[r['mappingCoverageTop80'] for r in results]; ov=[r['overlapVsNport'] for r in results]
 summary={'method':'Public HF all-market institutional 13F mirror; concentrated managers 10-120 assets and top10>=25%; same breadth score coefficients; conservative quarter-end+45d availability; PERMCO-to-ticker identity by multi-quarter raw-price fingerprint; compare Top80 to frozen N-PORT.', 'pilotPeriod':{'start':PILOT_START,'end':PILOT_END},'source':'kurry/institutional-holdings-13f-quarterly','sourceCoverage':'1980Q1-2024Q3','downloadedShards':SHARDS,'eligibleManagerCounts':eligible_counts,'targetSymbols':len(symbols),'mappedTargetSymbols':sum(1 for d in map_details.values() if d['permco']),'mappingCoverageTargetSymbols':sum(1 for d in map_details.values() if d['permco'])/len(symbols) if symbols else None,'months':len(results),'top80MappingCoverage':{'mean':statistics.mean(cov) if cov else None,'median':statistics.median(cov) if cov else None,'min':min(cov) if cov else None},'overlapVsNport':{'mean':statistics.mean(ov) if ov else None,'median':statistics.median(ov) if ov else None,'min':min(ov) if ov else None,'max':max(ov) if ov else None},'mappingDetails':map_details,'results':results,'limitations':['Mirror uses PERMCO and quarter-end dates, not original ticker/CUSIP/filing dates. +45 calendar days is deliberately conservative to avoid look-ahead.','13F concentrated institutional managers are an economic proxy for concentrated/thematic N-PORT ETFs, not the same filer population.','Price fingerprint is used solely for identifier mapping; ambiguous matches are rejected rather than forced.','Mirror provenance should be treated as secondary/public-research data until independently cross-checked against official SEC samples.']}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ['results','mappingDetails']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
