#!/usr/bin/env python3
from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/legacy-q1-index-discovery-sample-2006.json'
KNOWN=ROOT/'data/research/legacy-filing-index-series-pilot-2006.json'
OUT=ROOT/'data/research/legacy-q1-ticker-shape-diagnostic-2006.json'
def shape(t):
 t=(t or '').upper();return {'ticker':t,'endsX':t.endswith('X'),'length':len(t),'looksMutualFund':len(t)==5 and t.endswith('X'),'nonX':bool(t) and not t.endswith('X')}
def main():
 s=json.loads(SRC.read_text());k=json.loads(KNOWN.read_text());rows=[]
 for f in s['results']:
  for p in f.get('pairs',[]): rows.append({'company':f['company'],'dateFiled':f['dateFiled'],**p,**shape(p['ticker'])})
 known=[]
 for f in k['filings']:
  for p in f.get('pairs',[]):known.append({'company':f['label'],**p,**shape(p['ticker'])})
 nonx=[r for r in rows if r['nonX']];mf=[r for r in rows if r['looksMutualFund']]
 out={'purpose':'Diagnostic only: compare SEC filing-index ticker shapes in a deterministic Q1 N-Q sample with known 2006 ETF source filings. No ticker-shape rule is accepted by this script.','samplePairCount':len(rows),'sampleMutualLike5CharX':len(mf),'sampleNonX':len(nonx),'sampleNonXRate':len(nonx)/len(rows) if rows else 0,'sampleNonXRows':nonx,'knownPairCount':len(known),'knownNonX':sum(r['nonX'] for r in known),'knownMutualLike5CharX':sum(r['looksMutualFund'] for r in known),'knownRows':known,'lengthCounts':dict(Counter(r['length'] for r in rows))}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'sampleNonXRows','knownRows'}}),flush=True)
 for r in nonx:print('NONX',json.dumps(r),flush=True)
if __name__=='__main__':main()
