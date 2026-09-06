#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];r=ROOT/'data/research'

def compare(a,b):
    ar={x['symbol']:x['universeRank'] for x in a};br={x['symbol']:x['universeRank'] for x in b};common=set(ar)&set(br);k=min(len(a),len(b),80)
    overlap=len(common)/k if k else 1.0
    if len(common)>=2:
        n=len(common);d2=sum((ar[s]-br[s])**2 for s in common);rho=1-(6*d2)/(n*(n*n-1))
    else:rho=1.0 if len(common)==len(ar)==len(br) else None
    top=[x['symbol'] for x in a[:2]];ret=sum(s in br for s in top)/len(top) if top else 1.0
    return {'overlap':overlap,'spearman':rho,'top2Retention':ret,'commonCount':len(common),'k':k,'primaryTop2':top}

def main():
    sa=json.loads((r/'momentum-v2-9-authoritative-source-audit-v6-h1-2006.json').read_text())
    pa=json.loads((r/'momentum-v2-9-authoritative-holdings-audit-v5-h1-2006.json').read_text())
    mp=json.loads((r/'nq-hybrid-structural-mapping-h1-2006.json').read_text())
    co=json.loads((r/'nq-hybrid-country-resolved-h1-2006.json').read_text())
    pr=json.loads((r/'nq-hybrid-universe-h1-2006.json').read_text())
    up=json.loads((r/'nq-hybrid-universe-country-upper-bound-h1-2006.json').read_text())
    aid=int((r/'authoritative-holdings-v8-artifact-id.txt').read_text())
    allowed={'BASELINE_EXACT','BASELINE_ADR_BASE_UNIQUE','STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'};unexpected=sorted(set(mp.get('matchMethodCounts') or {})-allowed)
    mm={x['signalMonth']:x for x in mp['monthSnapshots']};cm={x['signalMonth']:x for x in co['monthSnapshots']};pm={x['signalMonth']:x for x in pr['monthSnapshots']};um={x['signalMonth']:x for x in up['monthSnapshots']};months=[]
    for month in sorted(pm):
        m=mm[month];c=cm[month];p=pm[month];u=um[month];mapped=known=0;mw=kw=0.0
        for f in c['sourceFilings']:
            for h in f.get('holdings',[]):
                if h.get('mappingStatus')!='MATCHED_UNIQUE':continue
                mapped+=1;w=float(h.get('weight') or 0);mw+=w
                if h.get('countryClassification') in {'US','NON_US'}:known+=1;kw+=w
        months.append({'signalMonth':month,'commonEquityHoldingCount':m['commonEquityHoldingCount'],'uniqueMappedCount':m['uniqueMappedCount'],'uniqueMappedCountRate':m['uniqueMappedCountRate'],'uniqueMappedWeightRate':m['uniqueMappedWeightRate'],'ambiguousCount':m['ambiguousCount'],'ambiguousWeight':m['ambiguousWeight'],'unmappedCount':m['unmappedCount'],'unmappedWeight':m['unmappedWeight'],'mappedCountryKnownCountRate':known/mapped if mapped else None,'mappedCountryKnownWeightRate':kw/mw if mw else None,'eligibleSourceSeriesCount':p['eligibleSourceSeriesCount'],'primaryUniverseSize':len(p['symbols']),'upperUniverseSize':len(u['symbols']),'upperComparison':compare(p['symbols'],u['symbols'])})
    conflicts=[]
    if any(sa.get(k) for k in ('umbrellaIdentityCount','internationalGrowthCount','vanguardAliasGroupCount','iSharesTrailingFundAliasGroupCount','ambiguousBridgeCount','postIdBoundaryQualificationFetchErrorCount')):conflicts.append('SOURCE_IDENTITY_BOUNDARY_OR_BRIDGE')
    parser_fields=('filingFetchErrorCount','missingCurrentSourceKeyCount','extraOutputSourceKeyCount','uniqueZeroHoldingTargetCount','uniqueNoGroupedTargetCount','ambiguousAssignedMarkerCount','badFinancialTextHoldingCount','temporalLabelHoldingCount','summaryAggregateHoldingCount')
    if any(pa.get(k) for k in parser_fields):conflicts.append('PARSER_STRUCTURAL_ERROR')
    if unexpected:conflicts.append('UNAPPROVED_NPX_MAPPING_METHOD')
    if co.get('currentTickerFallbackAllowed') is not False or co.get('currentTickerFallbackCount')!=0:conflicts.append('CURRENT_TICKER_COUNTRY_FALLBACK')
    if any(x['eligibleSourceSeriesCount']==0 or x['primaryUniverseSize']==0 for x in months):conflicts.append('EMPTY_SOURCE_OR_UNIVERSE')
    stable=all(x['upperComparison']['overlap']>=0.70 and (x['upperComparison']['spearman'] is None or x['upperComparison']['spearman']>=0.75) and x['upperComparison']['top2Retention']>=0.80 for x in months)
    if not stable:conflicts.append('COUNTRY_UPPER_BOUND_MATERIAL')
    out={'purpose':'Final return-independent Gate B v7 decision for Momentum v2.9 H1 2006 historical Universe reconstruction using source-v6 and exact-source-record-covered authoritative holdings v8.','authoritativeHoldingsArtifactId':aid,'frozenNpxMasterArtifactId':9876020712,'sourceIdentity':sa,'parsing':{k:pa.get(k) for k in ('uniqueSourceFilingCount','filingFetchSuccessCount','filingFetchErrorCount','uniqueParsedHoldingCount','assetSectionCounts','parseMethodCountsAcrossSnapshots','catalogKeyCount','outputKeyCount','missingCurrentSourceKeyCount','extraOutputSourceKeyCount','uniqueZeroHoldingTargetCount','uniqueNoGroupedTargetCount','ambiguousAssignedMarkerCount','badFinancialTextHoldingCount','temporalLabelHoldingCount','summaryAggregateHoldingCount')},'mappingMethodCounts':mp.get('matchMethodCounts'),'unexpectedMappingMethods':unexpected,'mappingUncertaintyPolicy':'AMBIGUOUS_AND_UNMAPPED_EXCLUDED_NOT_AUTO_ASSIGNED','country':{k:co.get(k) for k in ('countryEvidenceRule','currentTickerFallbackAllowed','currentTickerFallbackCount','unresolvedInputCount','resolvedUSCount','resolvedNonUSCount','remainingUnknownCount')},'countryUncertaintyPolicy':'UNKNOWN_EXCLUDED_PRIMARY; MAPPED_UNKNOWN_TO_US_ONLY_IN_UPPER_BOUND_SENSITIVITY','months':months,'countryUpperBoundSensitivityStable':stable,'structuralConflicts':conflicts,'gateBPass':not conflicts,'universeReconstructionConfirmed':not conflicts,'stage21PerformanceConsulted':False,'productionModified':False}
    (r/'momentum-v2-9-final-gate-b-v7-h1-2006.json').write_text(json.dumps(out,indent=2)+'\n')
    print('GATE_B_V7',json.dumps({k:v for k,v in out.items() if k!='months'}),flush=True)
    for x in months:print('MONTH',json.dumps(x),flush=True)
    if conflicts:raise SystemExit('Gate B v7 blockers: '+','.join(conflicts))
if __name__=='__main__':main()
