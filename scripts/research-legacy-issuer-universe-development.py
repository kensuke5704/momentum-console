#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT/'data'/'research'/'legacy-pit-holdings-development.json'
OUT = ROOT/'data'/'research'/'legacy-issuer-universe-development.json'
YEARS=(2006,2008,2010)

ss=importlib.util.spec_from_file_location('research_legacy_universe_score',ROOT/'scripts'/'research-legacy-universe-score.py')
score=importlib.util.module_from_spec(ss);sys.modules[ss.name]=score;ss.loader.exec_module(score)
es=importlib.util.spec_from_file_location('research_legacy_issuer_eligibility',ROOT/'scripts'/'research-legacy-issuer-eligibility.py')
eligibility=importlib.util.module_from_spec(es);sys.modules[es.name]=eligibility;es.loader.exec_module(eligibility)


def main():
    data=json.loads(INPUT.read_text())
    results={}
    for year in YEARS:
        rows=[r for r in data['records'] if r.get('year')==year and r.get('structurallyUsable') and r.get('holdings')]
        filings=[];status=Counter();included_weight=excluded_weight=0.0
        for r in rows:
            hs=[]
            for h in r['holdings']:
                cls=eligibility.classify(str(h.get('description') or ''),str(h.get('issuerKey') or ''))
                status[cls]+=1
                w=float(h.get('weight') or 0)
                if cls!='LEGACY_EQUITY_CANDIDATE':
                    excluded_weight+=w;continue
                included_weight+=w
                hs.append(score.Holding(h['issuerKey'],w))
            holdings=tuple(hs)
            if holdings:
                filings.append(score.Filing(str(r.get('accession') or ''),str(r['seriesId']),str(r.get('seriesName') or ''),str(r['filingDate']),holdings))
        if not filings:
            results[str(year)]={'sourceSeries':0,'universeSize':0,'top':[]};continue
        as_of=f'{year}-12-31'
        universe=score.build_universe(filings,as_of,80)
        results[str(year)]={
            'asOf':as_of,
            'sourceSeries':len(filings),
            'sourceIssuerKeys':len({h.symbol for f in filings for h in f.holdings}),
            'structuralClassCounts':dict(sorted(status.items())),
            'includedHoldingWeightAcrossSeries':included_weight,
            'excludedHoldingWeightAcrossSeries':excluded_weight,
            'eligibleRankedIssuerKeys':len(universe['symbols']),
            'universeSize':len(universe['symbols']),
            'top':[{'issuerKey':x['symbol'],'rank':x['universeRank'],'etfCount':x['etfCount'],'aggregateWeight':x['aggregateWeight'],'maxWeight':x['maxWeight'],'recencyWeight':x['recencyWeight'],'score':x['universeScore']} for x in universe['symbols'][:20]],
        }
        print(year,'series',len(filings),'issuerKeys',results[str(year)]['sourceIssuerKeys'],'eligible',len(universe['symbols']),'classes',dict(status),flush=True)
    out={
        'purpose':'Development-sample Universe breadth using contemporaneous filing-derived legacyIssuerKey only. No ticker/security-id mapping, prices, returns, or strategy performance are used.',
        'warning':'This is a deterministic 8-registrant-per-year feasibility sample, not yet the full historical Universe. Counts must not be interpreted as final Top80 coverage.',
        'scoringParity':'Same economic formula, eligibility and recency decay as frozen production Universe scorer.',
        'preRankingFilter':'Conservative structural classifier removes generic parser fragments, explicit non-equity/cash instruments, ADR/GDR non-US proxies, and LP/LLC non-corporate proxies before issuer-key ranking. No backfill.',
        'results':results,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({y:{k:v for k,v in r.items() if k!='top'} for y,r in results.items()},sort_keys=True),flush=True)

if __name__=='__main__':main()
