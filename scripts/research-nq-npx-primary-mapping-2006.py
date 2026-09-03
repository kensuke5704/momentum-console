#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/nq-npx-mapping-2006.json'; STRUCT=ROOT/'data/research/nq-npx-structural-mapping-2006.json'; AUD=ROOT/'data/research/nq-npx-suffix-match-audit-2006.json'; OUT=ROOT/'data/research/nq-npx-primary-mapping-2006.json'

def key(d): return (d.get('seriesId'),d.get('reportDate'),d.get('description'),round(float(d.get('weight') or 0),12))
def main():
    base=json.loads(BASE.read_text()); st=json.loads(STRUCT.read_text()); aud=json.loads(AUD.read_text())
    allowed={(r['seriesId'],r['description'],round(float(r['weight'] or 0),12)) for r in aud['rows'] if r.get('collisionFree')}
    sm={key(d):d for d in st.get('details',[])}
    details=[]; added=[]
    for b in base.get('details',[]):
        d=dict(b)
        if b.get('status')!='MATCHED_UNIQUE':
            s=sm.get(key(b))
            akey=(b.get('seriesId'),b.get('description'),round(float(b.get('weight') or 0),12))
            if s and s.get('status')=='MATCHED_UNIQUE' and s.get('matchMethod')=='STRUCTURAL_SUFFIX_EXACT' and akey in allowed:
                d=dict(s); d['matchMethod']='STRUCTURAL_SUFFIX_EXACT_COLLISION_FREE'; added.append(d)
        details.append(d)
    eligible=[d for d in details if d.get('status')!='PARSER_ARTIFACT']; matched=[d for d in eligible if d.get('status')=='MATCHED_UNIQUE']; amb=[d for d in eligible if d.get('status')=='AMBIGUOUS']; unm=[d for d in eligible if d.get('status')=='UNMAPPED']
    ew=sum(float(d.get('weight') or 0) for d in eligible); mw=sum(float(d.get('weight') or 0) for d in matched)
    out={k:v for k,v in base.items() if k not in {'details','series','topUnmappedByWeight','uniqueMatchedCount','uniqueMatchedCountRate','uniqueMatchedWeight','uniqueMatchedWeightRate','ambiguousCount','ambiguousWeight','unmappedCount','mappingRule'}}
    out.update({'purpose':'Primary 2006 mapping candidate frozen before historical Universe outcome evaluation: baseline deterministic mapping plus only collision-free exact issuer matches obtained by stripping trailing share-class/presentation suffixes. Unique long-prefix matches remain sensitivity-only and are excluded. No fuzzy auto-match or return/rank information used.','mappingRule':'Baseline deterministic exact/unique-ADR mapping plus STRUCTURAL_SUFFIX_EXACT only when the frozen N-PX issuer stem has one identity and the collision audit passes. UNIQUE_LONG_PREFIX excluded from primary.','eligibleHoldingCount':len(eligible),'eligibleHoldingWeight':ew,'uniqueMatchedCount':len(matched),'uniqueMatchedCountRate':len(matched)/len(eligible),'uniqueMatchedWeight':mw,'uniqueMatchedWeightRate':mw/ew,'ambiguousCount':len(amb),'ambiguousWeight':sum(float(d.get('weight') or 0) for d in amb),'unmappedCount':len(unm),'primarySuffixAddedCount':len(added),'primarySuffixAddedWeight':sum(float(d.get('weight') or 0) for d in added),'details':details,'topUnmappedByWeight':sorted(unm,key=lambda x:float(x.get('weight') or 0),reverse=True)[:50]})
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'details','topUnmappedByWeight'}}),flush=True)
if __name__=='__main__':main()
