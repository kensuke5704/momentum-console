#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'data/research'
OUT=DIR/'sec-etf-registrant-operational-prefilter-through-h2-2006.json'
H1=DIR/'sec-etf-registrant-operational-prefilter-h1-2006.json'
SOURCE_RUN_ID=34140039496
INVENTORY_ARTIFACT_ID=10025455602
H1_INPUT_ARTIFACT_ID=9962972058


def main():
    files=sorted(DIR.glob('sec-etf-registrant-operational-prefilter-through-h2-2006-shard-*.json'))
    if len(files)!=12: raise RuntimeError(f'expected 12 shards, found {len(files)}')
    payloads=[json.loads(p.read_text()) for p in files]
    idx=sorted(x['shardIndex'] for x in payloads)
    if idx!=list(range(12)): raise RuntimeError(f'shard indexes mismatch: {idx}')
    if any(x['shardCount']!=12 for x in payloads): raise RuntimeError('shardCount mismatch')
    if any(x.get('inventoryArtifactId')!=INVENTORY_ARTIFACT_ID for x in payloads): raise RuntimeError('inventoryArtifactId mismatch')

    results=[]
    for x in payloads: results.extend(x['results'])
    ciks=[r['cik'] for r in results]
    if len(ciks)!=len(set(ciks)): raise RuntimeError('duplicate registrant CIK across shards')
    full_counts={x['fullRegistrantCount'] for x in payloads}
    if len(full_counts)!=1: raise RuntimeError('fullRegistrantCount mismatch')
    full_count=next(iter(full_counts))
    if len(results)!=full_count: raise RuntimeError(f'merged registrants {len(results)} != expected {full_count}')
    results.sort(key=lambda r:r['cik'])

    current_pos=[r for r in results if r.get('candidateRegistrant')]
    current_ids={r['cik'] for r in current_pos}

    h1=json.loads(H1.read_text())
    h1_ids=set(h1['positiveCiks'])
    result_ids=set(ciks)
    missing_universe=sorted(h1_ids-result_ids)
    if missing_universe:
        raise RuntimeError(f'H1 candidate CIKs missing from cumulative 2006 N-Q universe: {missing_universe}')

    # Prefilter is recall-oriented only. A CIK that had PIT-valid candidate evidence in H1
    # must remain in the candidate pool even if a newer H2 filing no longer contains the broad
    # Creation-Unit/exchange text. Final acceptance is re-evaluated downstream with the unchanged
    # strict issuer-own Series-level rules; this carry-forward does not create a positive Series.
    carried_ids=sorted(h1_ids-current_ids)
    positive_ids=sorted(current_ids | h1_ids)

    current_by_cik={r['cik']:r for r in current_pos}
    h1_by_cik={r['cik']:r for r in h1.get('positiveCandidates',[])}
    positive_candidates=[]
    for cik in positive_ids:
        if cik in current_by_cik:
            positive_candidates.append({**current_by_cik[cik], 'candidateSource':'CURRENT_THROUGH_H2'})
        else:
            positive_candidates.append({**h1_by_cik[cik], 'candidateSource':'H1_CARRY_FORWARD'})

    out={
        'purpose':'Deterministic merge of the 12 cumulative-through-H2 2006 registrant operational-evidence prefilter shards with monotone H1 candidate carry-forward. The prefilter is recall-oriented only: a registrant with PIT-valid H1 candidate evidence remains eligible for downstream review even when its newest H2 filing no longer repeats broad ETF language. Final positive Series still require the unchanged strict issuer-own Series-level evidence and binding rules. No negative registrant is treated as a final ETF exclusion by this artifact.',
        'sourceRunId':SOURCE_RUN_ID,
        'inventoryArtifactId':INVENTORY_ARTIFACT_ID,
        'h1InputArtifactId':H1_INPUT_ARTIFACT_ID,
        'fullRegistrantCount':full_count,
        'currentPositiveCandidateRegistrantCount':len(current_ids),
        'h1PositiveCandidateRegistrantCount':len(h1_ids),
        'h1CarryForwardRegistrantCount':len(carried_ids),
        'h1CarryForwardCiks':carried_ids,
        'positiveCandidateRegistrantCount':len(positive_ids),
        'positiveCiks':positive_ids,
        'positiveCandidates':positive_candidates,
        'results':results,
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('results','positiveCandidates')}),flush=True)
    for r in positive_candidates:
        print('CANDIDATE',json.dumps({'cik':r['cik'],'candidateSource':r['candidateSource'],'companyNames':r.get('companyNames'),'positiveEvidence':r.get('positiveEvidence')}),flush=True)


if __name__=='__main__': main()
