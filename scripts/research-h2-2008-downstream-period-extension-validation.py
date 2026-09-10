#!/usr/bin/env python3
"""Frozen H2-2008 downstream exact-parity validator; no strategy data is read."""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data/research'
SOURCE_SHA='ed76ca73a204302f660aba4e79573766b9aa4ef9a25837db7f9843cd980ec110'
EXPECTED=[('2008-07','2008-07-31'),('2008-08','2008-08-29'),('2008-09','2008-09-30'),('2008-10','2008-10-31'),('2008-11','2008-11-28'),('2008-12','2008-12-31')]
ALLOWED={'BASELINE_EXACT','BASELINE_ADR_BASE_UNIQUE','STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'}

def read(name): return json.loads((DATA/name).read_text())
def evidence_dates(snap):
    for f in snap.get('sourceFilings',[]):
        for h in f.get('holdings',[]):
            if h.get('legacyAssetSection')!='COMMON_EQUITY' or h.get('mappingStatus')!='MATCHED_UNIQUE': continue
            for ev in h.get('countryEvidence') or []:
                if ev.get('evidenceDateFiled'): yield ev['evidenceDateFiled']
            ev=((h.get('countryResolutionEvidence') or {}).get('resolutionEvidence') or {})
            if ev.get('evidenceDateFiled'): yield ev['evidenceDateFiled']

def main():
    p=read('nq-holdings-parser-invariance-h1-h2-2008.json'); m=read('nq-series-id-structural-mapping-h2-2008.json')
    c=read('nq-series-id-country-pit-h2-2008.json'); d=read('nq-series-id-country-extension-diagnostic-h2-2008.json'); b=read('historical-universe-builder-h2-2008.json')
    ids={k:int(os.environ[k]) for k in ('PARSER_RUN_ID','PARSER_ARTIFACT_ID','MAPPING_RUN_ID','MAPPING_ARTIFACT_ID','COUNTRY_RUN_ID','COUNTRY_ARTIFACT_ID')}
    checks={}
    overlap=p.get('sourceCatalogOverlapCount')
    checks['parserInvariancePassed']=p.get('passed') is True and p.get('leftSourceArtifactId')==10088832684 and p.get('rightSourceArtifactId')==10131298181 and p.get('rightHoldingsArtifactId')==10131779818 and isinstance(overlap,int) and overlap>0 and p.get('holdingsOverlapCount')==overlap and p.get('semanticMismatchCount')==0 and p.get('sourceOnlyMissingFromHoldingsOverlapCount')==0 and p.get('holdingsOverlapNotInSourceOverlapCount')==0
    checks['mappingLineageFrozen']=m.get('sourceCatalogArtifactId')==10131298181 and m.get('sourceCatalogSha256')==SOURCE_SHA and m.get('holdingsRunId')==34423376664 and m.get('holdingsArtifactId')==10131779818 and m.get('npxPitRunId')==34423619035 and m.get('npxPitArtifactId')==10131980330 and m.get('npxBaseArtifactId')==10091573844 and m.get('mappingImplementationBlob')=='690479017fc82dce2480ded5d1ffafbb76721722' and set(m.get('matchMethodCounts',{}))<=ALLOWED and ids['MAPPING_RUN_ID']==34425023064 and ids['MAPPING_ARTIFACT_ID']>0
    checks['countryLineageFrozen']=all(x.get('catalogSha256')==SOURCE_SHA and x.get('sourceCatalogArtifactId')==10131298181 and x.get('sourceCatalogSha256')==SOURCE_SHA and x.get('mappingRunId')==34425023064 and x.get('mappingArtifactId')==ids['MAPPING_ARTIFACT_ID'] and x.get('npxPitRunId')==34423619035 and x.get('npxPitArtifactId')==10131980330 and x.get('npxBaseArtifactId')==10091573844 and x.get('periodExtensionMasterYears')==[2005,2006,2007,2008] for x in (c,d)) and ids['COUNTRY_RUN_ID']>0 and ids['COUNTRY_ARTIFACT_ID']>0
    checks['builderCatalogFrozen']=b.get('catalogSha256')==SOURCE_SHA
    rows=(m.get('monthSnapshots',[]),c.get('monthSnapshots',[]),d.get('monthSnapshots',[]),b.get('monthSnapshots',[])); checks['sixMonthCoverage']=all(len(x)==6 for x in rows)
    cardinality=no_lookahead=corp=parity=rank=True; monthly=[]
    if checks['sixMonthCoverage']:
        for want,ma,co,di,bu in zip(EXPECTED,*rows):
            month,asof=want; same=all((x.get('signalMonth'),x.get('asOf'))==want for x in (ma,co,di,bu)); count=ma.get('sourceSeriesCount')
            cardinality &= same and isinstance(count,int) and all(x.get('sourceSeriesCount')==count for x in (co,di,bu)) and ma.get('commonEquityHoldingCount')==co.get('commonEquityHoldingCount')
            dates=list(evidence_dates(co)); no_lookahead &= all(x<=asof for x in dates); corp &= co.get('corpPositiveNonCorpNameCount')==0
            exact=di.get('primaryEligibleSourceSeriesCount')==bu.get('eligibleSourceSeriesCount') and di.get('primarySymbols')==bu.get('symbols'); parity &= exact
            symbols=bu.get('symbols',[]); rank &= len(symbols)<=80 and [x.get('universeRank') for x in symbols]==list(range(1,len(symbols)+1))
            monthly.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':count,'eligibleSourceSeriesCount':bu.get('eligibleSourceSeriesCount'),'universeSize':len(symbols),'maxCountryEvidenceDate':max(dates) if dates else None,'corpPositiveNonCorpNameCount':co.get('corpPositiveNonCorpNameCount'),'exactBuilderParity':exact})
    else: cardinality=no_lookahead=corp=parity=rank=False
    checks.update({'periodCardinalityExact':cardinality,'countryNoLookahead':no_lookahead,'corpBridgeMaterialityInvariant':corp,'frozenBuilderExactParitySixOfSix':parity,'top80RankInvariant':rank})
    out={'purpose':'H2 2008 downstream period-extension exact-parity validation. It verifies fixed source/parser/mapping/N-PX/country lineage, PIT country no-lookahead, CORP bridge invariance, and exact six-month equality between the frozen historical-Universe builder and independent primary diagnostic. No strategy outcome is read.','definition':'docs/research/h2-2008-downstream-period-extension-validation-definition.md','sourceCatalogSha256':SOURCE_SHA,'parserInvarianceRunId':ids['PARSER_RUN_ID'],'parserInvarianceArtifactId':ids['PARSER_ARTIFACT_ID'],'checks':checks,'monthly':monthly,'passed':all(checks.values())}
    (DATA/'h2-2008-downstream-period-extension-validation.json').write_text(json.dumps(out,indent=2)+'\n')
    if not out['passed']: raise SystemExit(2)
if __name__=='__main__': main()
