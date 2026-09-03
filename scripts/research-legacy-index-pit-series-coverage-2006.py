#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IDX=ROOT/'data/research/legacy-filing-index-series-pilot-2006.json'
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
OUT=ROOT/'data/research/legacy-index-pit-series-coverage-2006.json'
def main():
 idx=json.loads(IDX.read_text());pit=json.loads(PIT.read_text())
 registry={p['seriesId']:p for f in idx['filings'] for p in f['pairs']}
 target=[]
 for r in pit['records']:
  sid=r.get('seriesId');ticks=r.get('fundTickers') or []
  target.append({'seriesId':sid,'seriesName':r.get('seriesName'),'pitTickers':ticks,'registry':registry.get(sid)})
 found=[r for r in target if r['registry']];missing=[r for r in target if not r['registry']]
 ticker_consistent=sum(1 for r in found if not r['pitTickers'] or r['registry']['ticker'] in r['pitTickers'])
 out={'purpose':'Metadata-only coverage check: determine whether every corrected EC-filtered 2006 PIT series is present in the SEC filing-index Series/Class/Ticker registry extracted from the same frozen source submissions. No holdings matching, ranks, or returns used.','pitSeriesCount':len(target),'registrySeriesCount':len(registry),'coveredSeriesCount':len(found),'seriesCoverageRate':len(found)/len(target) if target else 0,'tickerConsistentCoveredCount':ticker_consistent,'missing':missing,'covered':found}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'covered','missing'}}),flush=True);print('MISSING',json.dumps(missing),flush=True)
if __name__=='__main__':main()
