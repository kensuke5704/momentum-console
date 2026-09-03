#!/usr/bin/env python3
from __future__ import annotations
import glob,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/sec-country-evidence-cache-2006.json'; OUT=ROOT/'data/research/sec-country-evidence-cache-retry-2006.json'

def main():
    base=json.loads(BASE.read_text())
    rows={(r['ticker'],r['securityId']):dict(r) for r in base.get('rows',[])}
    for r in rows.values(): r['evidence']=list(r.get('evidence') or [])
    retry_files=sorted(glob.glob(str(ROOT/'data/research/sec-country-unknown-retry-*-2006.json')))
    if not retry_files: raise RuntimeError('no retry files found')
    added=0
    for f in retry_files:
        for rr in json.loads(Path(f).read_text()).get('results',[]):
            c=rr.get('classification')
            if c not in {'US','NON_US'}: continue
            k=(rr.get('ticker'),rr.get('securityId')); row=rows.get(k)
            if row is None: continue
            ev={'classification':c,'source':'UNKNOWN_RETRY','retryFile':Path(f).name,'resolutionSource':rr.get('resolutionSource'),'stateCode':rr.get('stateCode')}
            sig=(ev['classification'],ev.get('resolutionSource'),ev.get('stateCode'))
            existing={(e.get('classification'),e.get('resolutionSource'),e.get('stateCode')) for e in row['evidence']}
            if sig not in existing: row['evidence'].append(ev);added+=1
    conflicts=[]
    for row in rows.values():
        classes=sorted({e.get('classification') for e in row['evidence'] if e.get('classification') in {'US','NON_US'}})
        if len(classes)==1: row['classification']=classes[0]
        elif len(classes)>1: row['classification']='CONFLICT';conflicts.append(row)
        else: row['classification']='UNKNOWN'
    outrows=sorted(rows.values(),key=lambda r:(r.get('ticker') or '',r.get('securityId') or ''))
    out={'year':2006,'purpose':'Monotonic PIT issuer-country evidence cache after transport retry passes. Positive evidence is additive; UNKNOWN never overwrites positive evidence; conflicting positive evidence is surfaced as CONFLICT.','baseIdentityCount':base.get('identityCount'),'retryFileCount':len(retry_files),'addedEvidenceRecords':added,'identityCount':len(outrows),'classificationCounts':dict(Counter(r['classification'] for r in outrows)),'classificationWeights':{c:sum(float(r.get('aggregateWeight') or 0) for r in outrows if r['classification']==c) for c in ['US','NON_US','UNKNOWN','CONFLICT']},'conflictCount':len(conflicts),'rows':outrows,'conflicts':conflicts}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'rows','conflicts'}}),flush=True)
    for r in conflicts: print('CONFLICT',json.dumps(r),flush=True)
if __name__=='__main__':main()
