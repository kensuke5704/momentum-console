#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
LEFT_HOLDINGS=DATA/'nq-pit-holdings-series-id-h2-2007.json'
RIGHT_HOLDINGS=DATA/'nq-pit-holdings-series-id-h1-2008.json'
LEFT_SOURCE=DATA/'sec-id-era-strict-series-source-h2-2007.json'
RIGHT_SOURCE=DATA/'sec-id-era-strict-series-source-h1-2008.json'
OUT=DATA/'nq-holdings-parser-invariance-h2-2007-h1-2008.json'


def filing_key(row:dict)->tuple[str,str,str]:
    return (row.get('seriesId') or row.get('canonicalIdentity') or '',row.get('accession') or '',row.get('sourceFilename') or row.get('filename') or '')


def unique_holdings_records(payload:dict)->dict[tuple[str,str,str],dict]:
    out={}
    for snapshot in payload.get('monthSnapshots',[]):
        for row in snapshot.get('sourceFilings',[]):
            if row.get('identityRegime')!='SERIES_ID': continue
            key=filing_key(row)
            if not all(key): raise RuntimeError(f'incomplete Series-ID holdings filing key: {key}')
            previous=out.get(key)
            if previous is not None and previous!=row: raise RuntimeError(f'same holdings filing key has non-identical repeated record: {key}')
            out[key]=row
    return out


def unique_source_keys(payload:dict)->set[tuple[str,str,str]]:
    out=set()
    for snapshot in payload.get('monthSnapshots',[]):
        for row in snapshot.get('sourceFilings',[]):
            key=filing_key(row)
            if not all(key): raise RuntimeError(f'incomplete source-catalog filing key: {key}')
            out.add(key)
    return out


def parser_semantic_view(row:dict)->dict:
    return {k:v for k,v in row.items() if k!='legacyIdentity'}


def main()->None:
    left_payload=json.loads(LEFT_HOLDINGS.read_text()); right_payload=json.loads(RIGHT_HOLDINGS.read_text())
    left_source=json.loads(LEFT_SOURCE.read_text()); right_source=json.loads(RIGHT_SOURCE.read_text())
    left=unique_holdings_records(left_payload); right=unique_holdings_records(right_payload)
    holdings_overlap=sorted(set(left)&set(right)); source_overlap=sorted(unique_source_keys(left_source)&unique_source_keys(right_source))
    semantic=[]; legacy_only=[]; exact=0
    for key in holdings_overlap:
        l=left[key]; r=right[key]
        if l==r: exact+=1
        elif l.get('legacyIdentity')!=r.get('legacyIdentity'):
            legacy_only.append({'seriesId':key[0],'accession':key[1],'sourceFilename':key[2],'leftLegacyIdentity':l.get('legacyIdentity'),'rightLegacyIdentity':r.get('legacyIdentity')})
        lv=parser_semantic_view(l); rv=parser_semantic_view(r)
        if lv!=rv:
            semantic.append({'seriesId':key[0],'accession':key[1],'sourceFilename':key[2],'differingFields':sorted(f for f in set(lv)|set(rv) if lv.get(f)!=rv.get(f))})
    source_missing=sorted(set(source_overlap)-set(holdings_overlap)); holdings_extra=sorted(set(holdings_overlap)-set(source_overlap))
    passed=bool(source_overlap and set(holdings_overlap)==set(source_overlap) and not semantic)
    report={
        'purpose':'Parser-invariance audit across validated H2-2007 and H1-2008 Series-ID raw holdings. The overlap is derived independently from the current-period strict source snapshots supplied to both holdings runs. Every shared Series-ID + accession + SEC source-file key must occur in both holdings artifacts with exact parser-derived semantics, excluding only legacyIdentity schema metadata.',
        'leftPeriod':'H2-2007','rightPeriod':'H1-2008',
        'leftSourceArtifactId':10041257985,'rightSourceArtifactId':10088832684,
        'leftHoldingsArtifactId':10041328876,'rightHoldingsArtifactId':10091627801,
        'leftUniqueHoldingsFilingRecordCount':len(left),'rightUniqueHoldingsFilingRecordCount':len(right),
        'sourceCatalogOverlapCount':len(source_overlap),'holdingsOverlapCount':len(holdings_overlap),'exactFullRecordMatchCount':exact,
        'legacyIdentityOnlyDifferenceCount':len(legacy_only),'semanticMismatchCount':len(semantic),
        'sourceOnlyMissingFromHoldingsOverlapCount':len(source_missing),'holdingsOverlapNotInSourceOverlapCount':len(holdings_extra),
        'legacyIdentityOnlyDifferences':legacy_only,'semanticMismatches':semantic,
        'sourceOnlyMissingFromHoldingsOverlap':[list(k) for k in source_missing],
        'holdingsOverlapNotInSourceOverlap':[list(k) for k in holdings_extra],
        'passed':passed,
    }
    OUT.write_text(json.dumps(report,indent=2)+'\n')
    print('PARSER_INVARIANCE_H2_2007_H1_2008',json.dumps({k:report[k] for k in ('sourceCatalogOverlapCount','holdingsOverlapCount','exactFullRecordMatchCount','legacyIdentityOnlyDifferenceCount','semanticMismatchCount','sourceOnlyMissingFromHoldingsOverlapCount','holdingsOverlapNotInSourceOverlapCount','passed')}),flush=True)
    if not passed: raise SystemExit(2)

if __name__=='__main__': main()
