#!/usr/bin/env python3
import json,re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data/research/nq-npx-mapping-2006.json'
d=json.loads(p.read_text()); rows=d.get('details',[])
adr=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)
resolved=[]; unresolved=[]
for r in rows:
    if r.get('status')=='MATCHED_UNIQUE': continue
    reason=None
    if adr.search(r.get('description') or ''): reason='EXPLICIT_ADR_GDR'
    else:
        cands=r.get('diagnosticCandidates') or []
        ids=[]
        for c in cands:
            ids.extend(c.get('identities') or [])
        alpha={str(x.get('securityId') or '').upper() for x in ids if str(x.get('securityId') or '')[:1].isalpha()}
        if len(alpha)==1: reason='UNIQUE_DIAGNOSTIC_CINS_NON_US'
    (resolved if reason else unresolved).append({**r,'countryEvidence':reason} if reason else r)
summary={'totalEcHoldings':len(rows),'totalEcWeight':sum(float(r.get('weight') or 0) for r in rows),'nonMatchedCount':len(resolved)+len(unresolved),'nonMatchedWeight':sum(float(r.get('weight') or 0) for r in resolved+unresolved),'structuralNonUsCount':len(resolved),'structuralNonUsWeight':sum(float(r.get('weight') or 0) for r in resolved),'remainingNonMatchedCount':len(unresolved),'remainingNonMatchedWeight':sum(float(r.get('weight') or 0) for r in unresolved),'byReason':{k:{'count':sum(x['countryEvidence']==k for x in resolved),'weight':sum(float(x.get('weight') or 0) for x in resolved if x['countryEvidence']==k)} for k in sorted({x['countryEvidence'] for x in resolved})}}
print('SUMMARY',json.dumps(summary),flush=True)
out=Path(__file__).resolve().parents[1]/'data/research/country-unmapped-structural-audit-2006.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'summary':summary,'resolved':resolved},indent=2)+'\n')
