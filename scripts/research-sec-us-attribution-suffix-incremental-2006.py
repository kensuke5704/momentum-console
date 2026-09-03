#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
MAP=ROOT/'data/research/nq-npx-structural-mapping-2006.json'; AUD=ROOT/'data/research/nq-npx-suffix-match-audit-2006.json'; OUT=ROOT/'data/research/sec-us-attribution-suffix-incremental-2006.json'
ADR_RE=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)

def main():
    mp=json.loads(MAP.read_text()); aud=json.loads(AUD.read_text())
    allowed={(r['seriesId'],r['description'],float(r['weight'])) for r in aud['rows'] if r.get('collisionFree')}
    agg={}
    for d in mp.get('details',[]):
        if d.get('matchMethod')!='STRUCTURAL_SUFFIX_EXACT' or d.get('status')!='MATCHED_UNIQUE': continue
        keyrow=(d.get('seriesId'),d.get('description'),float(d.get('weight') or 0))
        if keyrow not in allowed: continue
        ident=d['identities'][0]; k=(ident['ticker'],ident['securityId'])
        x=agg.setdefault(k,{'ticker':ident['ticker'],'securityId':ident['securityId'],'issuer':d['description'],'asOfReportDate':d['reportDate'],'aggregateWeight':0.0,'occurrenceCount':0,'seriesIds':[],'issuerVariants':[]})
        x['aggregateWeight']+=float(d.get('weight') or 0);x['occurrenceCount']+=1
        if d.get('seriesId') not in x['seriesIds']:x['seriesIds'].append(d.get('seriesId'))
        if d.get('description') not in x['issuerVariants']:x['issuerVariants'].append(d.get('description'))
        if d['reportDate']<x['asOfReportDate']:x['asOfReportDate']=d['reportDate'];x['issuer']=d['description']
    results=[]
    for i,row in enumerate(sorted(agg.values(),key=lambda x:(x['ticker'],x['securityId'])),1):
        sid=(row.get('securityId') or '').upper(); desc=row.get('issuer') or ''
        if sid[:1].isalpha(): r={**row,'classification':'NON_US','resolutionSource':'CINS_ALPHA_PREFIX'}
        elif ADR_RE.search(desc): r={**row,'classification':'NON_US','resolutionSource':'EXPLICIT_ADR_GDR'}
        else: r=cur.resolve(row)
        results.append(r);print(f'{i}/{len(agg)}',json.dumps({k:r.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','classification','resolutionSource','stateCode']}),flush=True)
    classes=['US','NON_US','UNKNOWN']
    out={'purpose':'PIT country attribution only for the collision-free STRUCTURAL_SUFFIX_EXACT identities newly added beyond the frozen baseline mapping. Same country rules as the full 439-identity run; UNKNOWN preserved.','uniqueIdentityCount':len(results),'holdingOccurrenceCount':sum(r['occurrenceCount'] for r in results),'aggregateWeight':sum(r['aggregateWeight'] for r in results),'classificationCounts':{c:sum(r.get('classification')==c for r in results) for c in classes},'classificationWeights':{c:sum(r['aggregateWeight'] for r in results if r.get('classification')==c) for c in classes},'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
