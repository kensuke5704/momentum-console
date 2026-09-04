#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
SHARD_INDEX=int(os.environ.get('SHARD_INDEX','0'))
SHARD_COUNT=int(os.environ.get('SHARD_COUNT','1'))
OUT=ROOT/f'data/research/sec-submission-header-country-full-2006-shard-{SHARD_INDEX:02d}.json'
SPEC=importlib.util.spec_from_file_location('pilot',ROOT/'scripts'/'research-sec-submission-header-country-pilot-2006.py')
pilot=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(pilot)

def key(row):
    return (str(row.get('ticker') or ''),str(row.get('securityId') or ''),str(row.get('issuer') or ''),str(row.get('asOfReportDate') or ''))

def main():
    if SHARD_COUNT<1 or not (0<=SHARD_INDEX<SHARD_COUNT):raise ValueError('invalid shard configuration')
    data=json.loads(SRC.read_text())
    unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=key)
    selected=[r for i,r in enumerate(unknown) if i%SHARD_COUNT==SHARD_INDEX]
    years=sorted({int(r['asOfReportDate'][:4]) for r in unknown})
    master_rows,transports=pilot.base.load_master(years)
    results=[]
    for i,row in enumerate(selected,1):
        rec=pilot.resolve(row,master_rows)
        rec['occurrenceCount']=int(row.get('occurrenceCount') or 0)
        results.append(rec)
        print(f'{i}/{len(selected)}',json.dumps({k:rec.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','occurrenceCount','seedCik','seedSource','classification','stateCode','resolutionSource','evidenceForm','evidenceDateFiled']}),flush=True)
        time.sleep(.05)
    resolved=[r for r in results if r.get('classification') in ('US','NON_US')]
    counts={c:sum(1 for r in results if r.get('classification')==c) for c in ['US','NON_US','UNKNOWN']}
    out={
      'year':2006,
      'purpose':'Shard of the frozen full 180-identity remaining-UNKNOWN population. Uses the already validated PIT submission flat-header resolver without changing matching or country rules. Population order is deterministic lexical identity order and shard assignment is index modulo SHARD_COUNT; no holdings ranks, returns or strategy outcomes are used.',
      'shardIndex':SHARD_INDEX,'shardCount':SHARD_COUNT,'fullUnknownIdentityCount':len(unknown),'selectedIdentityCount':len(selected),
      'masterYears':years,'masterIndexTransports':transports,'classificationCounts':counts,
      'resolvedIdentityCount':len(resolved),'resolvedOccurrenceCount':sum(int(r.get('occurrenceCount') or 0) for r in resolved),
      'resolvedAggregateWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),
      'results':results
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('results','masterIndexTransports')}),flush=True)
if __name__=='__main__':main()
