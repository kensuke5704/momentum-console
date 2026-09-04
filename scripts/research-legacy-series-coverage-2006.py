#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIT=ROOT/'data/research/nq-pit-ec-filtered-2006.json'
IDX=ROOT/'data/research/legacy-filing-index-series-pilot-2006.json'
OUT=ROOT/'data/research/legacy-series-coverage-2006.json'

def collect_series(obj):
 out=[]
 for key in ('records','series','filings','results','portfolios'):
  v=obj.get(key)
  if isinstance(v,list):
   for r in v:
    if isinstance(r,dict):
     sid=r.get('seriesId') or r.get('seriesID')
     if sid:out.append(str(sid))
 for k in obj:
  if isinstance(k,str) and k.startswith('S') and len(k)==10:out.append(k)
 return sorted(set(out))

def main():
 pit=json.loads(PIT.read_text());idx=json.loads(IDX.read_text())
 pit_series=collect_series(pit);idx_series=sorted(set(idx.get('seriesIds',[])))
 matched=sorted(set(pit_series)&set(idx_series));missing=sorted(set(pit_series)-set(idx_series))
 out={'purpose':'Production-independent source-series coverage check: compare corrected 2006 PIT series against SEC filing-index series IDs from the same fixed source submissions. No holdings names, universe ranks, or returns used in discovery.','pitSeriesCount':len(pit_series),'indexSeriesCount':len(idx_series),'matchedCount':len(matched),'coverage':len(matched)/len(pit_series) if pit_series else None,'pitSeriesIds':pit_series,'matchedSeriesIds':matched,'missingSeriesIds':missing}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps(out),flush=True)
if __name__=='__main__':main()
