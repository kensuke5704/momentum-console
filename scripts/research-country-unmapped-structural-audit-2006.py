#!/usr/bin/env python3
import json,re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data/research/nq-npx-mapping-2006.json'
d=json.loads(p.read_text()); rows=d.get('details',[])
adr=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)
primary=[]; sensitivity=[]; unresolved=[]
for r in rows:
    if r.get('status')=='MATCHED_UNIQUE': continue
    if adr.search(r.get('description') or ''):
        primary.append({**r,'countryEvidence':'EXPLICIT_ADR_GDR'}); continue
    cands=r.get('diagnosticCandidates') or []; ids=[]
    for c in cands: ids.extend(c.get('identities') or [])
    alpha={str(x.get('securityId') or '').upper() for x in ids if str(x.get('securityId') or '')[:1].isalpha()}
    if len(alpha)==1:
        sensitivity.append({**r,'countryEvidence':'UNIQUE_DIAGNOSTIC_CINS_NON_US_SENSITIVITY_ONLY'})
    else: unresolved.append(r)
nonmatched=primary+sensitivity+unresolved
summary={'totalEcHoldings':len(rows),'totalEcWeight':sum(float(r.get('weight') or 0) for r in rows),'nonMatchedCount':len(nonmatched),'nonMatchedWeight':sum(float(r.get('weight') or 0) for r in nonmatched),'primaryStructuralNonUsCount':len(primary),'primaryStructuralNonUsWeight':sum(float(r.get('weight') or 0) for r in primary),'sensitivityOnlyCinsCount':len(sensitivity),'sensitivityOnlyCinsWeight':sum(float(r.get('weight') or 0) for r in sensitivity),'remainingNonMatchedCountPrimary':len(sensitivity)+len(unresolved),'remainingNonMatchedWeightPrimary':sum(float(r.get('weight') or 0) for r in sensitivity+unresolved)}
print('SUMMARY',json.dumps(summary),flush=True)
out=Path(__file__).resolve().parents[1]/'data/research/country-unmapped-structural-audit-2006.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'summary':summary,'primaryResolved':primary,'sensitivityOnly':sensitivity},indent=2)+'\n')
