#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'data/research'
COUNTRY=R/'nq-hybrid-country-resolved-h1-2006.json'
RECOVERY_DIR=R/'country-detail-recovery'


def key(ticker,security_id,report_date):
    return ((ticker or '').strip().upper(),security_id or None,report_date or None)


def main():
    country=json.loads(COUNTRY.read_text())
    files=sorted(RECOVERY_DIR.glob('country-filing-detail-recovery-v29-shard-*.json'))
    if len(files)!=8: raise RuntimeError(f'Expected 8 filing-detail shards, found {len(files)}')
    all_keys=set();recovered={};input_count=0
    for p in files:
        d=json.loads(p.read_text());input_count+=int(d.get('inputCount') or d.get('shardInputUnknownCount') or 0)
        if int(d.get('conflictCount') or 0): raise RuntimeError(f'Country conflict reported by {p}')
        for r in d.get('results',[]):
            k=key(r.get('ticker'),r.get('securityId'),r.get('asOfReportDate'))
            if k in all_keys: raise RuntimeError(f'Duplicate detail recovery key {k}')
            all_keys.add(k)
            cls=r.get('classification')
            if cls not in {'US','NON_US'}: continue
            if r.get('resolutionSource')!='PIT_FILING_DETAIL_ENTITY_STATE':
                raise RuntimeError(f'Unexpected detail source {k}: {r.get("resolutionSource")}')
            state=str(r.get('stateCode') or '').upper().strip()
            if not state or len(state)>3: raise RuntimeError(f'Invalid detail state code {k}: {state}')
            if not r.get('historicalExactCik') or not r.get('evidenceFilename') or not r.get('evidenceDateFiled'):
                raise RuntimeError(f'Incomplete filing-detail evidence {k}')
            recovered[k]=r

    audits=country.get('resolutionAudit',[])
    strict_keys={key(r.get('ticker'),r.get('securityId'),r.get('asOfReportDate')) for r in audits}
    unknown_before={key(r.get('ticker'),r.get('securityId'),r.get('asOfReportDate')) for r in audits if r.get('classification')=='UNKNOWN'}
    if set(recovered)-strict_keys: raise RuntimeError('Detail recovery contains keys absent from strict audit')
    if set(recovered)-unknown_before: raise RuntimeError('Detail recovery attempts to overwrite known strict country')

    promoted_audit=0
    for r in audits:
        k=key(r.get('ticker'),r.get('securityId'),r.get('asOfReportDate'));ev=recovered.get(k)
        if not ev: continue
        r.update({
            'classification':ev['classification'],'stateCode':ev.get('stateCode'),
            'resolutionSource':'PIT_FILING_DETAIL_ENTITY_STATE','seedCik':ev.get('historicalExactCik'),
            'evidenceForm':ev.get('evidenceForm'),'evidenceDateFiled':ev.get('evidenceDateFiled'),
            'evidenceFilename':ev.get('evidenceFilename'),'evidenceTransport':ev.get('evidenceTransport'),
            'filingDetailRecoveryEvidence':ev,
        });promoted_audit+=1
    if promoted_audit!=len(recovered): raise RuntimeError(f'Detail audit promotion mismatch {promoted_audit} vs {len(recovered)}')

    promoted_holdings=0;snapshots=[]
    for snap in country.get('monthSnapshots',[]):
        mc=Counter();mw=defaultdict(float);filings=[]
        for f in snap.get('sourceFilings',[]):
            report=f.get('reportDate');fc=Counter();fw=defaultdict(float);hs=[]
            for h0 in f.get('holdings',[]):
                h=dict(h0);cls=h.get('countryClassification','UNKNOWN')
                if cls=='UNKNOWN' and h.get('mappingStatus')=='MATCHED_UNIQUE':
                    ev=recovered.get(key(h.get('mappedTicker'),h.get('mappedSecurityId'),report))
                    if ev:
                        cls=ev['classification'];h['countryClassification']=cls
                        h['countryReason']='PIT_FILING_DETAIL_ENTITY_STATE';h['countryResolutionEvidence']=ev
                        promoted_holdings+=1
                w=float(h.get('weight') or 0);fc[cls]+=1;fw[cls]+=w;mc[cls]+=1;mw[cls]+=w;hs.append(h)
            filings.append({**{k:v for k,v in f.items() if k not in {'holdings','countryClassificationCounts','countryClassificationWeights'}},'countryClassificationCounts':dict(fc),'countryClassificationWeights':dict(fw),'holdings':hs})
        snapshots.append({**{k:v for k,v in snap.items() if k not in {'sourceFilings','countryClassificationCounts','countryClassificationWeights'}},'countryClassificationCounts':dict(mc),'countryClassificationWeights':dict(mw),'sourceFilings':filings})
    country['monthSnapshots']=snapshots
    country['resolvedUSCount']=sum(r.get('classification')=='US' for r in audits)
    country['resolvedNonUSCount']=sum(r.get('classification')=='NON_US' for r in audits)
    country['remainingUnknownCount']=sum(r.get('classification')=='UNKNOWN' for r in audits)
    country['filingDetailRecoveryAudit']={
        'rule':'Promote only strict-country UNKNOWN exact identity/report-date keys with the already-established unique historical CIK when a pre-report-date SEC filing-detail accession page binds the matching historical entity name and same CIK to exactly one State of Incorp. code. No current metadata, fuzzy matching, US default, ranks, returns or performance are used.',
        'recoveryShardCount':len(files),'recoveryInputCount':input_count,'recoveredIdentityDateCount':len(recovered),
        'recoveredUSCount':sum(x.get('classification')=='US' for x in recovered.values()),
        'recoveredNonUSCount':sum(x.get('classification')=='NON_US' for x in recovered.values()),
        'promotedAuditCount':promoted_audit,'promotedHoldingOccurrenceCount':promoted_holdings,
        'remainingUnknownCount':country['remainingUnknownCount'],'currentTickerFallbackAllowed':False,'outcomeDataConsulted':False,
    }
    country['currentTickerFallbackAllowed']=False;country['currentTickerFallbackCount']=0
    COUNTRY.write_text(json.dumps(country,indent=2)+'\n')
    print('DETAIL_COUNTRY_MERGE',json.dumps(country['filingDetailRecoveryAudit']),flush=True)

if __name__=='__main__':main()
