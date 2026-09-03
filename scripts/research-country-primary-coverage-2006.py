#!/usr/bin/env python3
from __future__ import annotations
import glob,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'data/research/nq-npx-primary-mapping-2006.json'; SUFFIX=ROOT/'data/research/sec-us-attribution-suffix-incremental-2006.json'; OUT=ROOT/'data/research/country-primary-coverage-2006.json'
ADR=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)

def main():
    mp=json.loads(MAP.read_text()); suffix=json.loads(SUFFIX.read_text())
    files=sorted(glob.glob(str(ROOT/'data/research/sec-us-attribution-full-shard-*-2006.json')))
    if len(files)!=12: raise RuntimeError(f'expected 12 base country shards, found {len(files)}')
    country={}; sources={}
    for f in files:
        for r in json.loads(Path(f).read_text()).get('results',[]):
            k=(r.get('ticker'),r.get('securityId')); country[k]=r.get('classification','UNKNOWN');sources[k]=r.get('resolutionSource')
    for r in suffix.get('results',[]):
        k=(r.get('ticker'),r.get('securityId'))
        # Same identity may already exist in baseline. Never overwrite a resolved historical classification with UNKNOWN.
        if k not in country or country[k]=='UNKNOWN': country[k]=r.get('classification','UNKNOWN');sources[k]=r.get('resolutionSource')
    rows=[]
    for d in mp.get('details',[]):
        x={'seriesId':d.get('seriesId'),'reportDate':d.get('reportDate'),'description':d.get('description'),'weight':float(d.get('weight') or 0),'mappingStatus':d.get('status'),'matchMethod':d.get('matchMethod')}
        if d.get('status')=='PARSER_ARTIFACT': x['countryClassification']='PARSER_ARTIFACT'
        elif d.get('status')=='MATCHED_UNIQUE' and len(d.get('identities',[]))==1:
            ident=d['identities'][0];k=(ident.get('ticker'),ident.get('securityId'));x['ticker']=k[0];x['securityId']=k[1];x['countryClassification']=country.get(k,'UNKNOWN');x['countryResolutionSource']=sources.get(k,'MISSING_COUNTRY_RESULT')
        elif ADR.search(d.get('description') or ''):
            x['countryClassification']='NON_US';x['countryResolutionSource']='EXPLICIT_ADR_GDR_UNMAPPED'
        else:
            x['countryClassification']='UNKNOWN';x['countryResolutionSource']='UNMAPPED_OR_AMBIGUOUS'
        rows.append(x)
    eligible=[r for r in rows if r['countryClassification']!='PARSER_ARTIFACT']; totalw=sum(r['weight'] for r in eligible)
    cls=['US','NON_US','UNKNOWN']
    counts={c:sum(r['countryClassification']==c for r in eligible) for c in cls}; weights={c:sum(r['weight'] for r in eligible if r['countryClassification']==c) for c in cls}
    mapped=[r for r in eligible if r['mappingStatus']=='MATCHED_UNIQUE']; mappedw=sum(r['weight'] for r in mapped)
    resolved=[r for r in eligible if r['countryClassification'] in {'US','NON_US'}]
    out={'year':2006,'purpose':'Primary full-holding country coverage after freezing the primary identity rule. UNKNOWN is excluded rather than imputed as US. Unmapped explicit ADR/GDR is strong NON_US evidence; fuzzy diagnostic CINS and unique-long-prefix mappings are excluded from primary. No strategy returns/ranks used.','rawEcHoldingCount':len(rows),'rawEcWeight':sum(r['weight'] for r in rows),'parserArtifactCount':sum(r['countryClassification']=='PARSER_ARTIFACT' for r in rows),'parserArtifactWeight':sum(r['weight'] for r in rows if r['countryClassification']=='PARSER_ARTIFACT'),'eligibleHoldingCount':len(eligible),'eligibleHoldingWeight':totalw,'primaryMappedCount':len(mapped),'primaryMappedCountRate':len(mapped)/len(eligible),'primaryMappedWeight':mappedw,'primaryMappedWeightRate':mappedw/totalw,'countryClassificationCounts':counts,'countryClassificationWeights':weights,'countryResolvedCount':len(resolved),'countryResolvedCountRate':len(resolved)/len(eligible),'countryResolvedWeight':sum(r['weight'] for r in resolved),'countryResolvedWeightRate':sum(r['weight'] for r in resolved)/totalw,'unknownCount':counts['UNKNOWN'],'unknownWeight':weights['UNKNOWN'],'usUsableCount':counts['US'],'usUsableWeight':weights['US'],'rows':rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
