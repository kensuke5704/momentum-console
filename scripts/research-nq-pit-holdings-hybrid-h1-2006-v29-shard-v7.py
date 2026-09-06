#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FULL=Path(os.environ.get('SOURCE_CATALOG_PATH',str(ROOT/'data/research/sec-hybrid-etf-source-catalog-h1-2006.json')))
IDX=int(os.environ['SHARD_INDEX']);COUNT=int(os.environ.get('SHARD_COUNT','4'))
TMP=ROOT/f'data/research/sec-hybrid-etf-source-catalog-shard-{IDX}.json'
OUT=ROOT/f'data/research/nq-pit-holdings-hybrid-h1-2006-shard-{IDX}.json'
def skey(s): return (str(s['cik']).zfill(10),s.get('accession') or '',s['filename'])
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(m);return m
def main():
 full=json.loads(FULL.read_text());keys=sorted({skey(s) for snap in full['monthSnapshots'] for s in snap['sourceFilings']});selected={k for i,k in enumerate(keys) if i%COUNT==IDX};snaps=[]
 for snap in full['monthSnapshots']:
  sources=[s for s in snap['sourceFilings'] if skey(s) in selected]
  snaps.append({**{k:v for k,v in snap.items() if k!='sourceFilings'},'sourceSeriesCount':len(sources),'legacySourceCount':sum(s.get('identityRegime')=='LEGACY_PRE_ID' for s in sources),'seriesIdSourceCount':sum(s.get('identityRegime')=='SERIES_ID' for s in sources),'sourceFilings':sources})
 TMP.parent.mkdir(parents=True,exist_ok=True);TMP.write_text(json.dumps({**{k:v for k,v in full.items() if k!='monthSnapshots'},'monthSnapshots':snaps},indent=2)+'\n')
 os.environ['CATALOG_PATH']=str(TMP)
 runner=load(f'runner_shard_v7_{IDX}',ROOT/'scripts/research-nq-pit-holdings-hybrid-h1-2006-v29final-v5.py');runner.hybrid.main()
 standard=ROOT/'data/research/nq-pit-holdings-hybrid-h1-2006.json';standard.replace(OUT)
 print('SHARD_V7_DONE',json.dumps({'shardIndex':IDX,'shardCount':COUNT,'uniqueFilingCount':len(selected)}),flush=True)
if __name__=='__main__':main()
