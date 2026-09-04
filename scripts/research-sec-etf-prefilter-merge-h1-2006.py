#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'data/research'
OUT=DIR/'sec-etf-registrant-operational-prefilter-h1-2006.json'
def main():
 files=sorted(DIR.glob('sec-etf-registrant-operational-prefilter-h1-2006-shard-*.json'))
 if len(files)!=12: raise RuntimeError(f'expected 12 shards, found {len(files)}')
 payloads=[json.loads(p.read_text()) for p in files]
 idx=sorted(x['shardIndex'] for x in payloads)
 if idx!=list(range(12)):raise RuntimeError(f'shard indexes mismatch: {idx}')
 if any(x['shardCount']!=12 for x in payloads):raise RuntimeError('shardCount mismatch')
 results=[]
 for x in payloads:results.extend(x['results'])
 ciks=[r['cik'] for r in results]
 if len(ciks)!=len(set(ciks)):raise RuntimeError('duplicate registrant CIK across shards')
 full_counts={x['fullRegistrantCount'] for x in payloads}
 if len(full_counts)!=1:raise RuntimeError('fullRegistrantCount mismatch')
 full_count=next(iter(full_counts))
 if len(results)!=full_count:raise RuntimeError(f'merged registrants {len(results)} != expected {full_count}')
 results.sort(key=lambda r:r['cik'])
 pos=[r for r in results if r.get('candidateRegistrant')]
 out={'purpose':'Deterministic merge of the 12 H1 2006 registrant operational-evidence prefilter shards. Positive registrants are candidates only and require subsequent series-level issuer-own-share evidence. No negative registrant is treated as a final ETF exclusion by this artifact.','sourceRunId':33897558123,'inventoryArtifactId':9946255797,'fullRegistrantCount':full_count,'positiveCandidateRegistrantCount':len(pos),'positiveCiks':[r['cik'] for r in pos],'positiveCandidates':pos,'results':results}
 OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('results','positiveCandidates')}),flush=True)
 for r in pos:print('CANDIDATE',json.dumps({'cik':r['cik'],'companyNames':r['companyNames'],'positiveEvidence':r.get('positiveEvidence')}),flush=True)
if __name__=='__main__':main()
