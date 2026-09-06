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
    files=sorted(R.glob('country-cover-state-recovery-v29-shard-*.json'))
    if len(files)!=8: raise RuntimeError(f'expected 8 cover-state shards, got {len(files)}')
    recovered={}; shard_summaries=[]
    for p in files:
        d=json.loads(p.read_text()); shard_summaries.append({k:d.get(k) for k in ('shardIndex','shardCikCount','recoveredCikCount','recoveredIdentityDateCount','fetchErrorCount')})
        for r in d.get('results',[]):
            if r.get('classification')!='US': continue
            k=key(r.get('ticker'),r.get('securityId'),r.get('asOfReportDate'))
            old=recovered.get(k)
            if old and (old.get('stateCode')!=r.get('stateCode') or old.get('historicalExactCik')!=r.get('historicalExactCik')):
                raise RuntimeError(f'conflicting cover-state evidence {k}')
            recovered[k]=r
    expected=sum(int(x.get('recoveredIdentityDateCount') or 0) for x in shard_summaries)
    if len(recovered)!=expected: raise RuntimeError(f'recovery key count {len(recovered)} != shard total {expected}')

    applied_audit=0
    for row in country.get('resolutionAudit',[]):
        k=key(row.get('ticker'),row.get('securityId'),row.get('asOfReportDate')); ev=recovered.get(k)
        if not ev: continue
        if row.get('classification') not in (None,'UNKNOWN'): raise RuntimeError(f'cover-state conflicts with existing country {k}')
        row.update({'classification':'US','resolutionSource':'PIT_FILING_COVER_US_JURISDICTION','stateCode':ev.get('stateCode'),'stateName':ev.get('stateName'),'seedCik':ev.get('historicalExactCik'),'evidenceForm':ev.get('evidenceForm'),'evidenceDateFiled':ev.get('evidenceDateFiled'),'submissionUrl':ev.get('evidenceSubmissionUrl'),'coverStateExtractMethod':ev.get('extractMethod'),'coverStateRecoveryApplied':True})
        applied_audit+=1
    if applied_audit!=len(recovered): raise RuntimeError(f'applied audit {applied_audit} != recovered {len(recovered)}')

    occurrence_applied=0
    for snap in country.get('monthSnapshots',[]):
        mc=Counter(); mw=defaultdict(float); filings=[]
        for filing in snap.get('sourceFilings',[]):
            rd=filing.get('reportDate'); fc=Counter(); fw=defaultdict(float); hs=[]
            for h in filing.get('holdings',[]):
                row=dict(h); k=key(row.get('mappedTicker'),row.get('mappedSecurityId'),rd); ev=recovered.get(k)
                if row.get('mappingStatus')=='MATCHED_UNIQUE' and row.get('countryClassification')=='UNKNOWN' and ev:
                    row['countryClassification']='US'; row['countryReason']='PIT_FILING_COVER_US_JURISDICTION'; row['countryResolutionEvidence']={'classification':'US','resolutionSource':'PIT_FILING_COVER_US_JURISDICTION','stateCode':ev.get('stateCode'),'stateName':ev.get('stateName'),'seedCik':ev.get('historicalExactCik'),'evidenceForm':ev.get('evidenceForm'),'evidenceDateFiled':ev.get('evidenceDateFiled'),'submissionUrl':ev.get('evidenceSubmissionUrl')}; occurrence_applied+=1
                cls=row.get('countryClassification','UNKNOWN'); w=float(row.get('weight') or 0); fc[cls]+=1;fw[cls]+=w;mc[cls]+=1;mw[cls]+=w;hs.append(row)
            filings.append({**{k:v for k,v in filing.items() if k not in {'holdings','countryClassificationCounts','countryClassificationWeights'}},'countryClassificationCounts':dict(fc),'countryClassificationWeights':dict(fw),'holdings':hs})
        snap['sourceFilings']=filings;snap['countryClassificationCounts']=dict(mc);snap['countryClassificationWeights']=dict(mw)
    country['resolvedUSCount']=int(country.get('resolvedUSCount') or 0)+len(recovered)
    country['remainingUnknownCount']=int(country.get('remainingUnknownCount') or 0)-len(recovered)
    if country['remainingUnknownCount']<0: raise RuntimeError('negative UNKNOWN count')
    country['coverStateRecovery']={'recoveredIdentityDateCount':len(recovered),'recoveredHoldingOccurrenceCount':occurrence_applied,'recoveredCikCount':sum(int(x.get('recoveredCikCount') or 0) for x in shard_summaries),'fetchErrorCount':sum(int(x.get('fetchErrorCount') or 0) for x in shard_summaries),'currentMetadataUsed':False,'fuzzyMatchingUsed':False,'returnsOrRanksUsed':False,'shards':shard_summaries}
    country['countryEvidenceRule']=(country.get('countryEvidenceRule') or '')+' -> PIT_FILING_COVER_US_JURISDICTION -> UNKNOWN'
    COUNTRY.write_text(json.dumps(country,indent=2)+'\n')
    print('COVER_STATE_APPLIED',json.dumps(country['coverStateRecovery']),flush=True)
    print('COUNTRY_COUNTS',json.dumps({'resolvedUSCount':country.get('resolvedUSCount'),'resolvedNonUSCount':country.get('resolvedNonUSCount'),'remainingUnknownCount':country.get('remainingUnknownCount')}),flush=True)
if __name__=='__main__': main()
