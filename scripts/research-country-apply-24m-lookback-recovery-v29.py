#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'data/research'
COUNTRY=R/'nq-hybrid-country-resolved-h1-2006.json'

def key(t,s,d): return ((t or '').strip().upper(),s or None,d or None)

def main():
    country=json.loads(COUNTRY.read_text())
    files=sorted(R.glob('country-24m-lookback-recovery-v29-shard-*.json'))
    if len(files)!=8: raise RuntimeError(f'expected 8 lookback shards, got {len(files)}')
    recovered={}; shard_summaries=[]; conflicts=0; errors=0
    for p in files:
        d=json.loads(p.read_text())
        shard_summaries.append({k:d.get(k) for k in ('shardIndex','shardInputCount','resolvedCount','resolvedUSCount','resolvedNonUSCount','ambiguousCikCount','conflictCount','fetchErrorCount')})
        conflicts+=int(d.get('conflictCount') or 0); errors+=int(d.get('fetchErrorCount') or 0)
        for r in d.get('results',[]):
            if r.get('classification') not in {'US','NON_US'}: continue
            k=key(r.get('ticker'),r.get('securityId'),r.get('asOfReportDate'))
            old=recovered.get(k)
            if old and (old.get('classification')!=r.get('classification') or old.get('seedCik')!=r.get('seedCik')):
                raise RuntimeError(f'conflicting 24m evidence for {k}')
            recovered[k]=r
    if conflicts:
        raise RuntimeError(f'24m recovery produced {conflicts} classification conflicts')
    expected=sum(int(x.get('resolvedCount') or 0) for x in shard_summaries)
    if len(recovered)!=expected: raise RuntimeError(f'recovered unique keys {len(recovered)} != shard resolved total {expected}')

    applied_audit=0
    for row in country.get('resolutionAudit',[]):
        k=key(row.get('ticker'),row.get('securityId'),row.get('asOfReportDate')); ev=recovered.get(k)
        if not ev: continue
        if row.get('classification') not in {None,'UNKNOWN'}:
            raise RuntimeError(f'24m evidence conflicts with existing country for {k}: {row.get("classification")}')
        row.update({
            'classification':ev['classification'],
            'resolutionSource':'PIT_SEC_24M_EXACT_NAME_UNIQUE_CIK_HEADER_STATE',
            'stateCode':ev.get('stateCode'),
            'observedStateCodes':ev.get('observedStateCodes') or [],
            'seedSource':'HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME_24M',
            'seedCik':ev.get('seedCik'),
            'evidenceForm':ev.get('evidenceForm'),
            'evidenceDateFiled':ev.get('evidenceDateFiled'),
            'evidenceFilename':ev.get('evidenceFilename'),
            'evidenceTransport':ev.get('evidenceTransport'),
            'lookbackDays':730,
            'lookbackRecoveryApplied':True,
        })
        applied_audit+=1
    if applied_audit!=len(recovered): raise RuntimeError(f'applied audit {applied_audit} != recovered {len(recovered)}')

    occurrence_applied=0; applied_classes=Counter()
    for snap in country.get('monthSnapshots',[]):
        mc=Counter();mw=defaultdict(float);filings=[]
        for filing in snap.get('sourceFilings',[]):
            rd=filing.get('reportDate');fc=Counter();fw=defaultdict(float);holdings=[]
            for h in filing.get('holdings',[]):
                row=dict(h);k=key(row.get('mappedTicker'),row.get('mappedSecurityId'),rd);ev=recovered.get(k)
                if row.get('mappingStatus')=='MATCHED_UNIQUE' and row.get('countryClassification')=='UNKNOWN' and ev:
                    cls=ev['classification'];row['countryClassification']=cls;row['countryReason']='PIT_SEC_24M_EXACT_NAME_UNIQUE_CIK_HEADER_STATE';row['countryResolutionEvidence']={'classification':cls,'resolutionSource':'PIT_SEC_24M_EXACT_NAME_UNIQUE_CIK_HEADER_STATE','stateCode':ev.get('stateCode'),'observedStateCodes':ev.get('observedStateCodes') or [],'seedCik':ev.get('seedCik'),'evidenceForm':ev.get('evidenceForm'),'evidenceDateFiled':ev.get('evidenceDateFiled'),'evidenceFilename':ev.get('evidenceFilename'),'lookbackDays':730};occurrence_applied+=1;applied_classes[cls]+=1
                cls=row.get('countryClassification','UNKNOWN');w=float(row.get('weight') or 0);fc[cls]+=1;fw[cls]+=w;mc[cls]+=1;mw[cls]+=w;holdings.append(row)
            filings.append({**{k:v for k,v in filing.items() if k not in {'holdings','countryClassificationCounts','countryClassificationWeights'}},'countryClassificationCounts':dict(fc),'countryClassificationWeights':dict(fw),'holdings':holdings})
        snap['sourceFilings']=filings;snap['countryClassificationCounts']=dict(mc);snap['countryClassificationWeights']=dict(mw)

    add_us=sum(1 for r in recovered.values() if r['classification']=='US'); add_nonus=sum(1 for r in recovered.values() if r['classification']=='NON_US')
    country['resolvedUSCount']=int(country.get('resolvedUSCount') or 0)+add_us
    country['resolvedNonUSCount']=int(country.get('resolvedNonUSCount') or 0)+add_nonus
    country['remainingUnknownCount']=int(country.get('remainingUnknownCount') or 0)-len(recovered)
    if country['remainingUnknownCount']<0: raise RuntimeError('remainingUnknownCount became negative')
    country['lookback24mRecovery']={'lookbackDays':730,'recoveredIdentityDateCount':len(recovered),'resolvedUSCount':add_us,'resolvedNonUSCount':add_nonus,'recoveredHoldingOccurrenceCount':occurrence_applied,'holdingOccurrenceClasses':dict(applied_classes),'conflictCount':conflicts,'fetchErrorCount':errors,'currentMetadataUsed':False,'fuzzyMatchingUsed':False,'returnsOrRanksUsed':False,'shards':shard_summaries}
    country['countryEvidenceRule']=(country.get('countryEvidenceRule') or '')+' -> PIT_SEC_24M_EXACT_NAME_UNIQUE_CIK_HEADER_STATE -> UNKNOWN'
    COUNTRY.write_text(json.dumps(country,indent=2)+'\n')
    print('LOOKBACK_24M_APPLIED',json.dumps(country['lookback24mRecovery']),flush=True)
    print('COUNTRY_COUNTS',json.dumps({'resolvedUSCount':country.get('resolvedUSCount'),'resolvedNonUSCount':country.get('resolvedNonUSCount'),'remainingUnknownCount':country.get('remainingUnknownCount')}),flush=True)
if __name__=='__main__': main()
