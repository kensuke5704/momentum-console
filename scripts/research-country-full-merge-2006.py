#!/usr/bin/env python3
from __future__ import annotations
import json,glob,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
MAPPING=DATA/'nq-npx-mapping-2006.json'
UNMAPPED=DATA/'country-unmapped-structural-audit-2006.json'
OUT=DATA/'country-full-coverage-2006.json'

def main():
    mapping=json.loads(MAPPING.read_text())
    shards=[]
    for p in sorted(glob.glob(str(DATA/'sec-us-attribution-full-shard-*-2006.json'))):
        shards.append(json.loads(Path(p).read_text()))
    if len(shards)!=12: raise RuntimeError(f'expected 12 shards, got {len(shards)}')
    by_ident={}
    identity_counts=Counter(); identity_weights=Counter()
    for s in shards:
        for r in s.get('results',[]):
            key=(str(r.get('ticker') or '').upper(),str(r.get('securityId') or '').upper())
            if key in by_ident and by_ident[key].get('classification')!=r.get('classification'):
                raise RuntimeError(f'conflicting classification {key}')
            by_ident[key]=r
            identity_counts[r.get('classification','UNKNOWN')]+=1
            identity_weights[r.get('classification','UNKNOWN')]+=float(r.get('aggregateWeight') or 0)
    rows=mapping.get('details',[])
    total_weight=sum(float(r.get('weight') or 0) for r in rows)
    holding_counts=Counter();holding_weights=Counter();resolution_sources=Counter();resolved_rows=[]
    explicit_adr=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)
    for r in rows:
        cls='UNKNOWN'; source=None
        if r.get('status')=='MATCHED_UNIQUE' and len(r.get('identities',[]))==1:
            ident=r['identities'][0];key=(str(ident.get('ticker') or '').upper(),str(ident.get('securityId') or '').upper())
            rr=by_ident.get(key)
            if rr:
                cls=rr.get('classification','UNKNOWN');source=rr.get('resolutionSource')
        elif explicit_adr.search(r.get('description') or ''):
            cls='NON_US';source='EXPLICIT_ADR_GDR_UNMAPPED'
        holding_counts[cls]+=1;holding_weights[cls]+=float(r.get('weight') or 0)
        if source: resolution_sources[source]+=1
        if cls!='UNKNOWN': resolved_rows.append({'seriesId':r.get('seriesId'),'description':r.get('description'),'weight':r.get('weight'),'classification':cls,'resolutionSource':source})
    resolved_count=holding_counts['US']+holding_counts['NON_US']
    resolved_weight=holding_weights['US']+holding_weights['NON_US']
    matched_rows=[r for r in rows if r.get('status')=='MATCHED_UNIQUE' and len(r.get('identities',[]))==1]
    matched_weight=sum(float(r.get('weight') or 0) for r in matched_rows)
    matched_resolved_count=sum(holding_counts.values()) # placeholder overwritten below
    mapped_h_counts=Counter();mapped_h_weights=Counter()
    for r in matched_rows:
        ident=r['identities'][0];rr=by_ident.get((str(ident.get('ticker') or '').upper(),str(ident.get('securityId') or '').upper()))
        cls=(rr or {}).get('classification','UNKNOWN');mapped_h_counts[cls]+=1;mapped_h_weights[cls]+=float(r.get('weight') or 0)
    summary={
      'year':2006,
      'purpose':'Full deterministic PIT country attribution coverage over all EC-filtered 2006 holdings. UNKNOWN is preserved; unmapped holdings are classified NON_US only with explicit ADR/GDR description. No fuzzy diagnostic candidate is used. No returns/ranks used.',
      'shardCount':len(shards),'uniqueMappedIdentityPopulation':len(by_ident),
      'identityClassificationCounts':dict(identity_counts),'identityClassificationWeights':dict(identity_weights),
      'ecHoldingCount':len(rows),'ecHoldingWeight':total_weight,
      'mappedUniqueHoldingCount':len(matched_rows),'mappedUniqueHoldingWeight':matched_weight,
      'mappedHoldingClassificationCounts':dict(mapped_h_counts),'mappedHoldingClassificationWeights':dict(mapped_h_weights),
      'mappedHoldingResolvedCountRate':(mapped_h_counts['US']+mapped_h_counts['NON_US'])/len(matched_rows) if matched_rows else None,
      'mappedHoldingResolvedWeightRate':(mapped_h_weights['US']+mapped_h_weights['NON_US'])/matched_weight if matched_weight else None,
      'allEcHoldingClassificationCounts':dict(holding_counts),'allEcHoldingClassificationWeights':dict(holding_weights),
      'allEcResolvedCountRate':resolved_count/len(rows) if rows else None,
      'allEcResolvedWeightRate':resolved_weight/total_weight if total_weight else None,
      'resolutionSources':dict(resolution_sources),
      'primaryUnmappedRule':'Only explicit ADR/GDR text can classify a non-MATCHED_UNIQUE row as NON_US. Diagnostic/fuzzy CINS remains sensitivity-only.',
    }
    OUT.write_text(json.dumps({'summary':summary,'resolvedRows':resolved_rows},indent=2)+'\n')
    print('SUMMARY',json.dumps(summary),flush=True)
if __name__=='__main__':main()
