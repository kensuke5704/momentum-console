#!/usr/bin/env python3
from __future__ import annotations
import json,glob
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
SHARD_DIR=ROOT/'data/research/shards'
OUT=ROOT/'data/research/sec-submission-header-country-full-merged-2006.json'
CLASSES=('US','NON_US','UNKNOWN')

def key(r):return (str(r.get('ticker') or ''),str(r.get('securityId') or ''),str(r.get('issuer') or ''),str(r.get('asOfReportDate') or ''))
def fdict(d):return {c:float(d.get(c,0) or 0) for c in CLASSES}
def idict(d):return {c:int(d.get(c,0) or 0) for c in CLASSES}

def main():
    src=json.loads(SRC.read_text())
    shard_files=sorted(glob.glob(str(SHARD_DIR/'sec-submission-header-country-full-2006-shard-*.json')))
    if not shard_files:raise RuntimeError('no shard files')
    shard_docs=[json.load(open(p)) for p in shard_files]
    results=[]
    for d in shard_docs:results.extend(d.get('results',[]))
    unknown=[r for r in src['identityRows'] if r.get('classification')=='UNKNOWN']
    expected={key(r) for r in unknown};seen=[key(r) for r in results]
    if len(seen)!=len(set(seen)):raise RuntimeError('duplicate shard identity')
    if set(seen)!=expected:raise RuntimeError(f'shard population mismatch expected={len(expected)} got={len(set(seen))}')
    resolved_by_key={key(r):r for r in results if r.get('classification') in ('US','NON_US')}
    merged=[]
    for r in src['identityRows']:
        nr=dict(r);rr=resolved_by_key.get(key(r))
        if rr:
            for field in ['classification','stateCode','resolutionSource','seedCik','seedSource','submissionUrl','historicalEntityName','evidenceForm','evidenceDateFiled','acceptanceDate','historicalExactCikCount','historicalExactCiks','filingCandidateCount','attempts']:
                if field in rr:nr[field]=rr[field]
        merged.append(nr)
    identity_counts={c:sum(1 for r in merged if r.get('classification')==c) for c in CLASSES}
    identity_weights={c:sum(float(r.get('aggregateWeight') or 0) for r in merged if r.get('classification')==c) for c in CLASSES}
    mapped_counts={c:sum(int(r.get('occurrenceCount') or 0) for r in merged if r.get('classification')==c) for c in CLASSES}
    mapped_weights={c:sum(float(r.get('aggregateWeight') or 0) for r in merged if r.get('classification')==c) for c in CLASSES}
    before_mapped_counts=idict(src['mappedHoldingClassificationCounts']);before_mapped_weights=fdict(src['mappedHoldingClassificationWeights'])
    before_all_counts=idict(src['allEcHoldingClassificationCounts']);before_all_weights=fdict(src['allEcHoldingClassificationWeights'])
    extras_counts={c:before_all_counts[c]-before_mapped_counts[c] for c in CLASSES}
    extras_weights={c:before_all_weights[c]-before_mapped_weights[c] for c in CLASSES}
    all_counts={c:mapped_counts[c]+extras_counts[c] for c in CLASSES}
    all_weights={c:mapped_weights[c]+extras_weights[c] for c in CLASSES}
    mapped_total=sum(mapped_counts.values());mapped_weight_total=sum(mapped_weights.values())
    all_total=sum(all_counts.values());all_weight_total=sum(all_weights.values())
    if mapped_total!=sum(before_mapped_counts.values()):raise RuntimeError('mapped count denominator changed')
    if abs(mapped_weight_total-sum(before_mapped_weights.values()))>1e-6:raise RuntimeError('mapped weight denominator changed')
    if all_total!=sum(before_all_counts.values()):raise RuntimeError('all-EC count denominator changed')
    if abs(all_weight_total-sum(before_all_weights.values()))>1e-6:raise RuntimeError('all-EC weight denominator changed')
    resolved=list(resolved_by_key.values());new_class=Counter(r['classification'] for r in resolved)
    new_occ={c:sum(int(r.get('occurrenceCount') or 0) for r in resolved if r['classification']==c) for c in ('US','NON_US')}
    new_weight={c:sum(float(r.get('aggregateWeight') or 0) for r in resolved if r['classification']==c) for c in ('US','NON_US')}
    out={
      'year':2006,
      'purpose':'Merge the validated PIT submission flat-header resolver across all 180 baseline mapped UNKNOWN identities and recompute baseline mapped/all-EC country coverage using the exact frozen denominators. Existing classifications and unmapped all-EC extras are unchanged; only formerly UNKNOWN mapped identities with historical name+CIK+state evidence move to US/NON_US.',
      'sourceArtifactId':9902743513,'shardFileCount':len(shard_files),'fullUnknownIdentityCount':len(unknown),
      'newlyResolvedIdentityCount':len(resolved),'newlyResolvedIdentityClassificationCounts':dict(new_class),
      'newlyResolvedOccurrenceCounts':new_occ,'newlyResolvedAggregateWeights':new_weight,
      'remainingUnknownIdentityCount':len(unknown)-len(resolved),
      'before':{
        'identityClassificationCounts':src['identityClassificationCounts'],'identityClassificationWeights':src['identityClassificationWeights'],
        'mappedHoldingClassificationCounts':src['mappedHoldingClassificationCounts'],'mappedHoldingClassificationWeights':src['mappedHoldingClassificationWeights'],
        'mappedHoldingResolvedCountRate':src['mappedHoldingResolvedCountRate'],'mappedHoldingResolvedWeightRate':src['mappedHoldingResolvedWeightRate'],
        'allEcHoldingClassificationCounts':src['allEcHoldingClassificationCounts'],'allEcHoldingClassificationWeights':src['allEcHoldingClassificationWeights'],
        'allEcResolvedCountRate':src['allEcResolvedCountRate'],'allEcResolvedWeightRate':src['allEcResolvedWeightRate']},
      'after':{
        'identityClassificationCounts':identity_counts,'identityClassificationWeights':identity_weights,
        'mappedHoldingClassificationCounts':mapped_counts,'mappedHoldingClassificationWeights':mapped_weights,
        'mappedHoldingResolvedCountRate':(mapped_counts['US']+mapped_counts['NON_US'])/mapped_total,
        'mappedHoldingResolvedWeightRate':(mapped_weights['US']+mapped_weights['NON_US'])/mapped_weight_total,
        'allEcHoldingClassificationCounts':all_counts,'allEcHoldingClassificationWeights':all_weights,
        'allEcResolvedCountRate':(all_counts['US']+all_counts['NON_US'])/all_total,
        'allEcResolvedWeightRate':(all_weights['US']+all_weights['NON_US'])/all_weight_total},
      'unmappedAllEcExtrasPreserved':{'counts':extras_counts,'weights':extras_weights},
      'shardSummaries':[{k:d.get(k) for k in ['shardIndex','shardCount','selectedIdentityCount','classificationCounts','resolvedIdentityCount','resolvedOccurrenceCount','resolvedAggregateWeight']} for d in shard_docs],
      'identityRows':merged
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('identityRows','shardSummaries')}),flush=True)
if __name__=='__main__':main()
