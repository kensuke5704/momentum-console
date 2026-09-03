#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
IDX=int(os.environ['SHARD_INDEX']);COUNT=int(os.environ['SHARD_COUNT'])
OUT=ROOT/f'data/research/sec-historical-name-validate-shard-{IDX:02d}-of-{COUNT:02d}-2006.json'
SPEC=importlib.util.spec_from_file_location('v',ROOT/'scripts'/'research-sec-ticker-seed-historical-name-validate-2006.py')
v=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(v)
cur=v.cur;old=v.old

def main():
 data=json.loads(SRC.read_text());unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or ''))
 shard=[r for i,r in enumerate(unknown) if i%COUNT==IDX];rows=[]
 for i,row in enumerate(shard,1):
  target=old.normalize_name(row['issuer']);rec={k:row.get(k) for k in ['ticker','securityId','issuer','asOfReportDate','aggregateWeight']};rec['classification']='UNKNOWN'
  seeds=cur.CM.get(str(row['ticker']).upper(),[]);ciks=sorted(set(x['cik'] for x in seeds));rec['tickerSeedCiks']=ciks
  if len(ciks)==1:
   try:
    b=old.browse_cik(ciks[0],row['asOfReportDate']);rec['seedCik']=ciks[0];rec['archiveCount']=len(b.get('archiveUrls',[]))
    for url in b.get('archiveUrls',[])[:16]:
     val=v.archive_validate(url,target)
     if val:rec.update(val);rec['resolutionSource']='CURRENT_TICKER_CIK_HISTORICAL_NAME_VALIDATED';break
   except Exception as e:rec['error']=type(e).__name__
  rows.append(rec);print(f'{i}/{len(shard)}',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','classification','stateCode','seedCik']}),flush=True);time.sleep(.05)
 out={'purpose':'Shard over all residual UNKNOWN identities using current ticker only as CIK seed; classification requires historical COMPANY CONFORMED NAME match plus filing-time state/country.','shardIndex':IDX,'shardCount':COUNT,'populationCount':len(unknown),'rowCount':len(rows),'resolvedCount':sum(r['classification']!='UNKNOWN' for r in rows),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows if r['classification']!='UNKNOWN'),'rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
