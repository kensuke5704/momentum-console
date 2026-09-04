#!/usr/bin/env python3
from __future__ import annotations
import json,glob
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
MAP=ROOT/'data/research/nq-npx-mapping-2006.json'
OUT=ROOT/'data/research/country-full-coverage-canonical-merge-2006.json'

def key(r): return (str(r.get('ticker') or ''),str(r.get('securityId') or ''))
def main():
 base=json.loads(BASE.read_text());mapping=json.loads(MAP.read_text())
 shard_rows=[]
 for p in sorted(glob.glob(str(ROOT/'data/research/sec-filing-index-country-canonical-shard-*-2006.json'))):
  shard_rows.extend(json.loads(Path(p).read_text()).get('rows',[]))
 updates={key(r):r for r in shard_rows if r.get('classification') in {'US','NON_US'}}
 merged=[];changed={}
 for r0 in base['identityRows']:
  r=dict(r0);k=key(r)
  if r.get('classification')=='UNKNOWN' and k in updates:
   u=updates[k];old='UNKNOWN';r.update({x:u.get(x) for x in ['classification','stateCode','seedCik','currentTitle','indexUrl','transport','resolutionSource'] if u.get(x) is not None});changed[k]=(old,r['classification'])
  merged.append(r)
 id_counts=Counter(r.get('classification','UNKNOWN') for r in merged);id_weights=Counter()
 for r in merged:id_weights[r.get('classification','UNKNOWN')]+=float(r.get('aggregateWeight') or 0)
 lookup={key(r):r.get('classification','UNKNOWN') for r in merged}
 mh_counts=Counter();mh_weights=Counter();changed_h_count=0;changed_h_weight=0.0
 for d in mapping['details']:
  if d.get('status')!='MATCHED_UNIQUE' or len(d.get('identities') or [])!=1:continue
  i=d['identities'][0];k=(str(i.get('ticker') or ''),str(i.get('securityId') or ''));cls=lookup.get(k,'UNKNOWN');w=float(d.get('weight') or 0)
  mh_counts[cls]+=1;mh_weights[cls]+=w
  if k in changed:changed_h_count+=1;changed_h_weight+=w
 # Preserve baseline all-EC treatment of unmapped/ambiguous rows exactly; only transfer holdings whose mapped identity changed from UNKNOWN.
 ae_counts=Counter(base['allEcHoldingClassificationCounts']);ae_weights=Counter({k:float(v) for k,v in base['allEcHoldingClassificationWeights'].items()})
 for d in mapping['details']:
  if d.get('status')!='MATCHED_UNIQUE' or len(d.get('identities') or [])!=1:continue
  i=d['identities'][0];k=(str(i.get('ticker') or ''),str(i.get('securityId') or ''))
  if k not in changed:continue
  new=changed[k][1];w=float(d.get('weight') or 0);ae_counts['UNKNOWN']-=1;ae_counts[new]+=1;ae_weights['UNKNOWN']-=w;ae_weights[new]+=w
 total_count=sum(ae_counts.values());total_weight=sum(ae_weights.values());resolved_count=ae_counts['US']+ae_counts['NON_US'];resolved_weight=ae_weights['US']+ae_weights['NON_US']
 out={'year':2006,'purpose':'Merge baseline PIT country classifications with the frozen canonical corporate-designator SEC filing-index shard resolver. Baseline non-UNKNOWN classifications are immutable. Only baseline UNKNOWN identities may be upgraded. All-EC unmapped/ambiguous handling is preserved exactly from the baseline artifact.','baselineArtifactId':9902743513,'canonicalShardRunId':33856052345,'canonicalShardRowCount':len(shard_rows),'canonicalResolvedIdentityCount':len(changed),'canonicalChangedMappedHoldingCount':changed_h_count,'canonicalChangedMappedHoldingWeight':changed_h_weight,'identityClassificationCounts':dict(id_counts),'identityClassificationWeights':dict(id_weights),'mappedHoldingClassificationCounts':dict(mh_counts),'mappedHoldingClassificationWeights':dict(mh_weights),'allEcHoldingClassificationCounts':dict(ae_counts),'allEcHoldingClassificationWeights':dict(ae_weights),'allEcResolvedCountRate':resolved_count/total_count if total_count else None,'allEcResolvedWeightRate':resolved_weight/total_weight if total_weight else None,'identityRows':merged}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='identityRows'}),flush=True)
if __name__=='__main__':main()
