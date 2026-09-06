#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / 'data/research'
COUNTRY = R / 'nq-hybrid-country-resolved-h1-2006.json'
RECOVERY = R / 'country-foreign-form-recovery-v29.json'


def key(ticker, security_id, report_date):
    return ((ticker or '').strip().upper(), security_id or None, report_date or None)


def main():
    country=json.loads(COUNTRY.read_text())
    recovery=json.loads(RECOVERY.read_text())
    recovered={
        key(r.get('ticker'),r.get('securityId'),r.get('asOfReportDate')):r
        for r in recovery.get('results',[])
        if r.get('classification')=='NON_US'
    }
    if len(recovered) != int(recovery.get('resolvedNonUSCount') or 0):
        raise RuntimeError('recovery key cardinality mismatch')

    audit_applied=0
    for row in country.get('resolutionAudit',[]):
        k=key(row.get('ticker'),row.get('securityId'),row.get('asOfReportDate'))
        ev=recovered.get(k)
        if not ev:
            continue
        if row.get('classification') not in {None,'UNKNOWN'}:
            raise RuntimeError(f'foreign-form evidence conflicts with existing classification: {k} {row.get("classification")}')
        row.update({
            'classification':'NON_US',
            'resolutionSource':'PIT_SEC_MASTER_STRONG_FOREIGN_ISSUER_FORM',
            'seedSource':'HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME',
            'seedCik':ev.get('seedCik'),
            'foreignIssuerEvidenceForms':ev.get('evidenceForms') or ev.get('strongForeignForms') or [],
            'foreignFormRecoveryApplied':True,
        })
        audit_applied += 1
    if audit_applied != len(recovered):
        raise RuntimeError(f'expected {len(recovered)} recovery audit rows, applied {audit_applied}')

    occurrence_applied=0
    for snapshot in country.get('monthSnapshots',[]):
        month_counts=Counter(); month_weights=defaultdict(float)
        filings=[]
        for filing in snapshot.get('sourceFilings',[]):
            report_date=filing.get('reportDate')
            fcounts=Counter(); fweights=defaultdict(float)
            holdings=[]
            for holding in filing.get('holdings',[]):
                row=dict(holding)
                k=key(row.get('mappedTicker'),row.get('mappedSecurityId'),report_date)
                if row.get('mappingStatus')=='MATCHED_UNIQUE' and row.get('countryClassification')=='UNKNOWN' and k in recovered:
                    row['countryClassification']='NON_US'
                    row['countryReason']='PIT_SEC_MASTER_STRONG_FOREIGN_ISSUER_FORM'
                    row['countryResolutionEvidence']={
                        'classification':'NON_US',
                        'resolutionSource':'PIT_SEC_MASTER_STRONG_FOREIGN_ISSUER_FORM',
                        'seedCik':recovered[k].get('seedCik'),
                        'evidenceForms':recovered[k].get('evidenceForms') or recovered[k].get('strongForeignForms') or [],
                    }
                    occurrence_applied += 1
                cls=row.get('countryClassification','UNKNOWN')
                w=float(row.get('weight') or 0.0)
                fcounts[cls]+=1; fweights[cls]+=w
                month_counts[cls]+=1; month_weights[cls]+=w
                holdings.append(row)
            filings.append({
                **{k:v for k,v in filing.items() if k not in {'holdings','countryClassificationCounts','countryClassificationWeights'}},
                'countryClassificationCounts':dict(fcounts),
                'countryClassificationWeights':dict(fweights),
                'holdings':holdings,
            })
        snapshot['sourceFilings']=filings
        snapshot['countryClassificationCounts']=dict(month_counts)
        snapshot['countryClassificationWeights']=dict(month_weights)

    original_nonus=int(country.get('resolvedNonUSCount') or 0)
    original_unknown=int(country.get('remainingUnknownCount') or 0)
    country['resolvedNonUSCount']=original_nonus + len(recovered)
    country['remainingUnknownCount']=original_unknown - len(recovered)
    if country['remainingUnknownCount'] < 0:
        raise RuntimeError('remainingUnknownCount became negative')
    country['foreignFormRecovery']={
        'inputArtifactRule':'PIT SEC historical master index only',
        'automaticRule':'historical cleaned exact issuer name -> exactly one CIK before report date AND 20-F/40-F/6-K reporting form -> NON_US',
        'recoveredIdentityDateCount':len(recovered),
        'recoveredHoldingOccurrenceCount':occurrence_applied,
        'currentTickerMetadataUsed':False,
        'fuzzyMatchingUsed':False,
        'returnsOrRanksUsed':False,
    }
    country['countryEvidenceRule']=(country.get('countryEvidenceRule') or '') + ' -> PIT_SEC_MASTER_STRONG_FOREIGN_ISSUER_FORM -> UNKNOWN'
    COUNTRY.write_text(json.dumps(country,indent=2)+'\n')
    print('FOREIGN_FORM_RECOVERY_APPLIED',json.dumps(country['foreignFormRecovery']),flush=True)
    print('COUNTRY_COUNTS',json.dumps({'resolvedUSCount':country.get('resolvedUSCount'),'resolvedNonUSCount':country.get('resolvedNonUSCount'),'remainingUnknownCount':country.get('remainingUnknownCount')}),flush=True)

if __name__=='__main__':
    main()
