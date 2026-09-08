#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'data/research'
OUT=DIR/'sec-etf-registrant-operational-prefilter-through-h2-2007.json'
PRIOR=DIR/'sec-etf-registrant-operational-prefilter-through-h1-2007.json'
SOURCE_RUN_ID=34187156944
INVENTORY_ARTIFACT_ID=10040860433
PRIOR_INPUT_ARTIFACT_ID=10039881783


def main():
    files=sorted(DIR.glob('sec-etf-registrant-operational-prefilter-through-h2-2007-shard-*.json'))
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

    prior=json.loads(PRIOR.read_text())
    prior_ids=set(prior['positiveCiks'])
    result_ids=set(ciks)
    missing_universe=sorted(prior_ids-result_ids)
    if missing_universe:
        raise RuntimeError(f'prior candidate CIKs missing from cumulative N-Q universe: {missing_universe}')

    # Candidate prefilter remains monotone for recall only. Final Series acceptance is
    # independently re-established downstream and is never inherited from this carry-forward.
    carried_ids=sorted(prior_ids-current_ids)
    positive_ids=sorted(current_ids | prior_ids)

    current_by_cik={r['cik']:r for r in current_pos}
    prior_by_cik={r['cik']:r for r in prior.get('positiveCandidates',[])}
    positive_candidates=[]
    for cik in positive_ids:
        if cik in current_by_cik:
            positive_candidates.append({**current_by_cik[cik], 'candidateSource':'CURRENT_THROUGH_H2_2007'})
        else:
            if cik not in prior_by_cik:
                raise RuntimeError(f'prior positive candidate payload missing for {cik}')
            positive_candidates.append({**prior_by_cik[cik], 'candidateSource':'H1_2007_CARRY_FORWARD'})

    out={
        'purpose':'Deterministic merge of the 12 cumulative-through-H2-2007 registrant operational-evidence prefilter shards with monotone authoritative H1-2007 candidate carry-forward. The prefilter is recall-oriented only: a registrant with PIT-valid prior candidate evidence remains eligible for downstream review even when a newer filing no longer repeats broad ETF language. Final positive Series still require the unchanged strict issuer-own Series-level evidence and binding rules. No negative registrant is treated as a final ETF exclusion by this artifact.',
        'sourceRunId':SOURCE_RUN_ID,
        'inventoryArtifactId':INVENTORY_ARTIFACT_ID,
        'priorInputArtifactId':PRIOR_INPUT_ARTIFACT_ID,
        'fullRegistrantCount':full_count,
        'currentPositiveCandidateRegistrantCount':len(current_ids),
        'priorPositiveCandidateRegistrantCount':len(prior_ids),
        'priorCarryForwardRegistrantCount':len(carried_ids),
        'priorCarryForwardCiks':carried_ids,
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
