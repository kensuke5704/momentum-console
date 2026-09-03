#!/usr/bin/env python3
from __future__ import annotations
import json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'data/research/nq-npx-structural-mapping-2006.json'; NPX=ROOT/'data/research/npx-security-master-2006.json'; OUT=ROOT/'data/research/nq-npx-suffix-match-audit-2006.json'

def norm(s): return ' '.join(re.sub(r'[^A-Z0-9]+',' ',str(s).upper().replace('&',' AND ')).split())
def base_name(s):
    s=norm(s)
    s=re.sub(r'\b(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$','',s).strip()
    return s

def main():
    mp=json.loads(MAP.read_text()); master=json.loads(NPX.read_text())
    # Build all valid identities grouped by issuer stem, retaining every ticker/securityId seen in the frozen N-PX master.
    bystem=defaultdict(set)
    for r in master.get('records',[]):
        t=(r.get('ticker') or '').strip().upper(); sid=(r.get('securityId') or '').strip().upper()
        if not t or not sid: continue
        stem=base_name(r.get('normalizedIssuer') or r.get('issuer') or '')
        if stem: bystem[stem].add((t,sid))
    rows=[]
    for d in mp.get('details',[]):
        if d.get('matchMethod')!='STRUCTURAL_SUFFIX_EXACT' or d.get('status')!='MATCHED_UNIQUE': continue
        ident=(d['identities'][0]['ticker'],d['identities'][0]['securityId'])
        stem=base_name(d.get('matchedAlias') or d.get('description') or '')
        pool=sorted(bystem.get(stem,set()))
        rows.append({
          'description':d.get('description'),'weight':d.get('weight'),'seriesId':d.get('seriesId'),
          'matchedIdentity':{'ticker':ident[0],'securityId':ident[1]},'issuerStem':stem,
          'masterIdentityPool':[{'ticker':t,'securityId':s} for t,s in pool],
          'poolIdentityCount':len(pool),'collisionFree':len(pool)==1 and pool[0]==ident,
        })
    summary={'suffixMatchCount':len(rows),'suffixMatchWeight':sum(float(r['weight'] or 0) for r in rows),'collisionFreeCount':sum(r['collisionFree'] for r in rows),'collisionFreeWeight':sum(float(r['weight'] or 0) for r in rows if r['collisionFree']),'collisionRows':sum(not r['collisionFree'] for r in rows)}
    print('SUMMARY',json.dumps(summary),flush=True)
    for r in rows:
        if not r['collisionFree']: print('COLLISION',json.dumps(r),flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'summary':summary,'rows':rows},indent=2)+'\n')
if __name__=='__main__':main()
