#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IN_DIR=ROOT/'data/research/preid-shards'
OUT=ROOT/'data/research/sec-legacy-etf-series-source-preid-2006.json'
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28')]

def main():
    paths=sorted(IN_DIR.glob('sec-legacy-etf-series-source-preid-2006-shard-*.json'))
    if not paths: raise RuntimeError('no pre-ID shards found')
    shards=[json.loads(p.read_text()) for p in paths]
    shard_counts={int(s['shards']) for s in shards}
    if len(shard_counts)!=1: raise RuntimeError(f'inconsistent shard counts {sorted(shard_counts)}')
    expected=next(iter(shard_counts))
    shard_ids=sorted(int(s['shard']) for s in shards)
    if len(paths)!=expected or shard_ids!=list(range(expected)):
        raise RuntimeError(f'expected shards 0..{expected-1}, got {shard_ids}')
    assigned=[c for s in shards for c in s['assignedCiks']]
    if len(assigned)!=47 or len(set(assigned))!=47:
        raise RuntimeError(f'assigned CIK invariant failed total={len(assigned)} unique={len(set(assigned))}')
    occ={}
    for s in shards:
        for r in s['sourceOccurrences']:
            key=(r['legacyIdentity'],r.get('sourceAccession') or r['sourceFilename'])
            old=occ.get(key)
            if old and old!=r: raise RuntimeError(f'conflicting occurrence {key}')
            occ[key]=r
    occurrences=list(occ.values())
    identities={}
    for r in sorted(occurrences,key=lambda x:(x['evidenceDateFiled'],x['legacyIdentity'],x['evidenceFilename'])):
        identities.setdefault(r['legacyIdentity'],r)
    snapshots=[]
    for month,asof in MONTHS:
        latest={}
        for r in occurrences:
            if r['sourceFilingDate']>asof or r['evidenceDateFiled']>asof: continue
            cur=latest.get(r['legacyIdentity'])
            if cur is None or (r['sourceFilingDate'],r.get('sourceAccession') or '')>(cur['sourceFilingDate'],cur.get('sourceAccession') or ''):
                latest[r['legacyIdentity']]=r
        src=sorted(latest.values(),key=lambda x:(x['cik'],x['normalizedSeriesName']))
        snapshots.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(src),'sourceFilings':src})
    binding=Counter(r['binding'] for r in identities.values());forms=Counter(r['sourceForm'] for r in occurrences)
    out={
        'purpose':f'Merged strict pre-Series-ID complete-portfolio ETF source catalog through 2006-02-05. {expected}-way CIK sharding changes execution topology only; selection semantics are unchanged. Contemporary schedule titles require same-CIK issuer-own Creation Unit plus exchange evidence and Series-level ETF binding. A normalized title exactly equal to the SEC registrant/company name is rejected as a non-Series identity. No later Series IDs, holdings outcomes, ranks, returns, or strategy results are used.',
        'seriesIdMandatoryDate':'2006-02-06','sourceCutoff':'2006-02-05','evidenceCutoff':'2006-02-28','shardCount':expected,
        'candidateRegistrantCount':len(set(assigned)),
        'candidateSourceFilingCount':sum(s['candidateSourceFilingCount'] for s in shards),
        'candidateRegistrantWithSourceFilingCount':len({r['cik'] for s in shards for r in s['sourceAudit']}),
        'operationalEvidenceFilingCount':sum(s['operationalEvidenceFilingCount'] for s in shards),
        'positiveIdentityCount':len(identities),'bindingCounts':dict(sorted(binding.items())),
        'sourceOccurrenceCount':len(occurrences),'sourceFormCounts':dict(sorted(forms.items())),
        'sourceNoScheduleCount':sum(s['sourceNoScheduleCount'] for s in shards),
        'amendmentNoScheduleCount':sum(s['amendmentNoScheduleCount'] for s in shards),
        'prospectusErrorCount':sum(s['prospectusErrorCount'] for s in shards),
        'sourceErrorCount':sum(s['sourceErrorCount'] for s in shards),
        'positiveIdentities':sorted(identities.values(),key=lambda x:x['legacyIdentity']),
        'sourceOccurrences':sorted(occurrences,key=lambda x:(x['legacyIdentity'],x['sourceFilingDate'],x.get('sourceAccession') or '')),
        'monthSnapshots':snapshots,
        'prospectusAudit':[r for s in shards for r in s['prospectusAudit']],
        'sourceAudit':[r for s in shards for r in s['sourceAudit']],
        'masterTransports':[r for s in shards for r in s.get('masterTransports',[])],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('positiveIdentities','sourceOccurrences','monthSnapshots','prospectusAudit','sourceAudit','masterTransports')}),flush=True)
    for s in snapshots: print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)
if __name__=='__main__':main()
