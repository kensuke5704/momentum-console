#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/'data/universe-history.json';BOOT=ROOT/'data/sec-nport/bootstrap.json.gz';OUT=ROOT/'data/research/gate-b-production-source-contribution-2020.json'
DAY=86400

def months(raw):
 if isinstance(raw,list):return raw
 if isinstance(raw,dict):
  for k in ('months','history'):
   if isinstance(raw.get(k),list):return raw[k]
  return [v for v in raw.values() if isinstance(v,dict) and v.get('signalMonth')]
 return []

def main():
 hist=json.loads(HIST.read_text());m=next(x for x in months(hist) if x.get('signalMonth')=='2020-01');asof=m['asOf']
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 snaps=b.get('snapshots',b) if isinstance(b,dict) else b
 srcids={x['seriesId'] for x in m.get('sourceFilings',[])}
 latest={}
 for f in snaps:
  sid=f.get('seriesId')
  if sid not in srcids or f.get('filingDate','')>asof:continue
  cur=latest.get(sid)
  if not cur or (f.get('filingDate',''),f.get('accession',''))>(cur.get('filingDate',''),cur.get('accession','')):latest[sid]=f
 prod={x['symbol']:x for x in m.get('symbols',[])}
 details=[]
 for symbol,p in prod.items():
  contrib=[]
  for sid,f in latest.items():
   hs=[h for h in f.get('holdings',[]) if (h.get('symbol') or '').upper()==symbol]
   if hs:
    contrib.append({'seriesId':sid,'seriesName':f.get('seriesName'),'weight':sum(float(h.get('weight') or 0) for h in hs),'filingDate':f.get('filingDate'),'reportDate':f.get('reportDate')})
  details.append({'symbol':symbol,'universeRank':p.get('universeRank'),'universeScore':p.get('universeScore'),'etfCount':p.get('etfCount'),'aggregateWeight':p.get('aggregateWeight'),'maxWeight':p.get('maxWeight'),'contributions':contrib})
 print('SOURCES',json.dumps([{'seriesId':k,'seriesName':v.get('seriesName'),'holdings':len(v.get('holdings',[]))} for k,v in latest.items()]),flush=True)
 for r in details:print('SYMBOL',json.dumps(r),flush=True)
 # Counterfactual score/rank using each subset of source series, directly on frozen Production holdings.
 subsets=[];sids=sorted(latest)
 for mask in range(1,1<<len(sids)):
  use=[sids[i] for i in range(len(sids)) if mask>>i&1];rows={}
  for sid in use:
   f=latest[sid]
   for h in f.get('holdings',[]):
    sym=(h.get('symbol') or '').upper();w=float(h.get('weight') or 0)
    if not sym or w<=0:continue
    x=rows.setdefault(sym,{'sids':set(),'agg':0.,'max':0.,'rec':0.});x['sids'].add(sid);x['agg']+=w;x['max']=max(x['max'],w);x['rec']+=w # relative only; all same transition region
  ranked=[]
  for sym,x in rows.items():
   n=len(x['sids'])
   if n<2 and x['max']<4:continue
   score=3*math.log1p(n)+.5*math.log1p(x['agg'])+.5*math.log1p(x['rec']);ranked.append((score,n,x['agg'],sym))
  ranked.sort(key=lambda x:(-x[0],-x[1],-x[2],x[3]));top=[x[3] for x in ranked[:80]];ps=list(prod)
  common=set(top)&set(ps)
  subsets.append({'seriesIds':use,'candidateSize':len(top),'production9Retained':len(common),'production9RetentionRate':len(common)/len(ps) if ps else None,'retainedSymbols':sorted(common),'missingProductionSymbols':sorted(set(ps)-set(top))})
 for r in subsets:print('SUBSET',json.dumps(r),flush=True)
 out={'purpose':'Decompose the actual 2020-01 Production Universe into its three N-PORT source-series contributions and measure source-subset sensitivity using frozen Production holdings only. This does not validate legacy reconstruction; it identifies which exact source series are material to Gate B.','details':details,'subsets':subsets}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
