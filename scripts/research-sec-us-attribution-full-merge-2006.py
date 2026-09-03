#!/usr/bin/env python3
from __future__ import annotations
import glob,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'data/research/nq-npx-mapping-2006.json'
UNMAPPED=ROOT/'data/research/country-unmapped-structural-audit-2006.json'
OUT=ROOT/'data/research/sec-us-attribution-full-summary-2006.json'

def main():
    mapping=json.loads(MAP.read_text()); unm=json.loads(UNMAPPED.read_text())
    files=sorted(glob.glob(str(ROOT/'data/research/sec-us-attribution-full-shard-*-2006.json')))
    if len(files)!=12: raise RuntimeError(f'Expected 12 shard files, found {len(files)}')
    results=[]
    for f in files: results.extend(json.loads(Path(f).read_text()).get('results',[]))
    keys=[(r['ticker'],r['securityId']) for r in results]
    if len(results)!=439 or len(set(keys))!=439: raise RuntimeError(f'Expected 439 unique identities, got {len(results)} rows / {len(set(keys))} unique')
    classes=['US','NON_US','UNKNOWN']
    identityCounts={k:sum(r.get('classification')==k for r in results) for k in classes}
    mappedWeights={k:sum(float(r.get('aggregateWeight') or 0) for r in results if r.get('classification')==k) for k in classes}
    mappedHoldingOccurrences={k:sum(int(r.get('occurrenceCount') or 0) for r in results if r.get('classification')==k) for k in classes}
    sources=Counter(r.get('resolutionSource') or 'UNKNOWN' for r in results)
    totalEcWeight=float(mapping.get('eligibleHoldingWeight') or sum(float(r.get('weight') or 0) for r in mapping.get('details',[])))
    totalEcCount=len(mapping.get('details',[]))
    mappedWeight=sum(mappedWeights.values()); mappedCount=sum(mappedHoldingOccurrences.values())
    primaryNonmatchedWeight=float(unm['summary']['primaryStructuralNonUsWeight']); primaryNonmatchedCount=int(unm['summary']['primaryStructuralNonUsCount'])
    sensitivityWeight=float(unm['summary']['sensitivityOnlyCinsWeight']); sensitivityCount=int(unm['summary']['sensitivityOnlyCinsCount'])
    resolvedMappedWeight=mappedWeights['US']+mappedWeights['NON_US']; resolvedMappedCount=mappedHoldingOccurrences['US']+mappedHoldingOccurrences['NON_US']
    primaryResolvedWeight=resolvedMappedWeight+primaryNonmatchedWeight; primaryResolvedCount=resolvedMappedCount+primaryNonmatchedCount
    sensitivityResolvedWeight=primaryResolvedWeight+sensitivityWeight; sensitivityResolvedCount=primaryResolvedCount+sensitivityCount
    out={
      'year':2006,
      'purpose':'Full deterministic PIT country-attribution coverage summary over the active 936 EC holdings. Primary evidence uses deterministic mapped identity + CINS/explicit ADR-GDR/historical SEC filing; unmapped fuzzy candidate CINS is sensitivity-only. UNKNOWN is never treated as US. No returns or Universe ranks used.',
      'totalEcHoldings':totalEcCount,'totalEcWeight':totalEcWeight,
      'uniqueMappedIdentityCount':len(results),'mappedHoldingCount':mappedCount,'mappedHoldingWeight':mappedWeight,
      'identityClassificationCounts':identityCounts,'mappedHoldingClassificationCounts':mappedHoldingOccurrences,'mappedClassificationWeights':mappedWeights,
      'resolutionSources':dict(sources),
      'unmappedPrimaryExplicitAdrGdrCount':primaryNonmatchedCount,'unmappedPrimaryExplicitAdrGdrWeight':primaryNonmatchedWeight,
      'unmappedSensitivityCandidateCinsCount':sensitivityCount,'unmappedSensitivityCandidateCinsWeight':sensitivityWeight,
      'primaryResolvedHoldingCount':primaryResolvedCount,'primaryResolvedHoldingCountRate':primaryResolvedCount/totalEcCount,
      'primaryResolvedWeight':primaryResolvedWeight,'primaryResolvedWeightRate':primaryResolvedWeight/totalEcWeight,
      'primaryUnknownHoldingCount':totalEcCount-primaryResolvedCount,'primaryUnknownWeight':totalEcWeight-primaryResolvedWeight,
      'sensitivityResolvedHoldingCount':sensitivityResolvedCount,'sensitivityResolvedHoldingCountRate':sensitivityResolvedCount/totalEcCount,
      'sensitivityResolvedWeight':sensitivityResolvedWeight,'sensitivityResolvedWeightRate':sensitivityResolvedWeight/totalEcWeight,
      'results':results,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
