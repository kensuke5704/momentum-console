#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'
HOLDINGS = DATA / 'nq-pit-holdings-series-id-h1-2008.json'
NPX_AUDIT = DATA / 'npx-pit-master-h1-2008-audit.json'
OUT = DATA / 'nq-series-id-structural-mapping-h1-2008.json'
TMP = DATA / 'h1-2008-mapping-tmp'
SOURCE_ARTIFACT_ID = 10088832684
SOURCE_SHA = '31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc'
NPX_BASE_ARTIFACT_ID = 10041975282
MAPPING_BLOB = '690479017fc82dce2480ded5d1ffafbb76721722'
EXPECTED_DATES = [
    ('2008-01','2008-01-31'),('2008-02','2008-02-29'),('2008-03','2008-03-31'),
    ('2008-04','2008-04-30'),('2008-05','2008-05-30'),('2008-06','2008-06-30'),
]
ALLOWED_METHODS = {'BASELINE_EXACT','BASELINE_ADR_BASE_UNIQUE','STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'}
MAPPING_FIELDS = {'mappingStatus','matchMethod','matchedAlias','identities','mappedTicker','mappedSecurityId'}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def master_path(signal_month: str) -> Path:
    return DATA / f'npx-pit-master-h1-2008-{signal_month}.json'


def strip_mapping_fields(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in MAPPING_FIELDS}


def validate_holdings_lineage(payload: dict) -> list[tuple[str,str,int]]:
    if payload.get('sourceCatalogArtifactId') != SOURCE_ARTIFACT_ID or payload.get('sourceCatalogSha256') != SOURCE_SHA:
        raise RuntimeError('unexpected H1-2008 holdings source lineage')
    if payload.get('authoritativeH1HoldingsRunId') != 34089965073 or payload.get('authoritativeH1HoldingsArtifactId') != 10006530879:
        raise RuntimeError('unexpected authoritative H1 parser lineage')
    observed = [(s.get('signalMonth'), s.get('asOf'), s.get('catalogSourceSeriesCount')) for s in payload.get('monthSnapshots', [])]
    if [(m,d) for m,d,_ in observed] != EXPECTED_DATES:
        raise RuntimeError(f'unexpected H1-2008 holdings month boundary: {observed}')
    return observed


def validate_npx(audit: dict, monthly: dict[str,dict]) -> None:
    if audit.get('status') != 'PASS' or audit.get('fetchErrorCount') != 0 or audit.get('violations'):
        raise RuntimeError('H1-2008 PIT N-PX audit is not PASS/clean')
    if audit.get('baseRunId') != 34190105652 or audit.get('baseArtifactId') != NPX_BASE_ARTIFACT_ID:
        raise RuntimeError('unexpected H2-2007 N-PX base lineage')
    if [(m.get('signalMonth'),m.get('asOf')) for m in audit.get('monthly',[])] != EXPECTED_DATES:
        raise RuntimeError('PIT N-PX audit does not contain exact six H1-2008 months')
    for month, as_of in EXPECTED_DATES:
        master = monthly[month]
        if master.get('signalMonth') != month or master.get('asOf') != as_of:
            raise RuntimeError(f'wrong PIT N-PX master assigned to {month}')
        if master.get('baseRunId') != 34190105652 or master.get('baseArtifactId') != NPX_BASE_ARTIFACT_ID:
            raise RuntimeError(f'wrong N-PX base lineage in {month}')
        for row in master.get('records',[]):
            filing_date=row.get('sourceFilingDate'); admitted_at=row.get('admittedAtSignal')
            if isinstance(filing_date,str) and filing_date.startswith('2008-') and filing_date > as_of:
                raise RuntimeError(f'N-PX filing lookahead in {month}: {filing_date}>{as_of}')
            if isinstance(admitted_at,str) and admitted_at > as_of:
                raise RuntimeError(f'N-PX admission lookahead in {month}: {admitted_at}>{as_of}')


def validate_mapped_month(input_snap: dict, output_snap: dict) -> None:
    if (output_snap.get('signalMonth'),output_snap.get('asOf'),output_snap.get('sourceSeriesCount')) != (input_snap.get('signalMonth'),input_snap.get('asOf'),len(input_snap.get('sourceFilings',[]))):
        raise RuntimeError('mapped month boundary/source-Series count changed')
    if len(input_snap.get('sourceFilings',[])) != len(output_snap.get('sourceFilings',[])):
        raise RuntimeError('source filing count changed during mapping')
    for inp,out in zip(input_snap.get('sourceFilings',[]),output_snap.get('sourceFilings',[])):
        for key,value in inp.items():
            if key == 'holdings': continue
            if out.get(key) != value: raise RuntimeError(f'source filing field changed during mapping: {key}')
        expected_holdings=[h for h in inp.get('holdings',[]) if h.get('legacyAssetSection')=='COMMON_EQUITY']
        actual_holdings=out.get('holdings',[])
        if len(expected_holdings)!=len(actual_holdings): raise RuntimeError('COMMON_EQUITY holding count changed during mapping')
        for before,after in zip(expected_holdings,actual_holdings):
            if strip_mapping_fields(after)!=before: raise RuntimeError('base COMMON_EQUITY holding fields changed during mapping')
            status=after.get('mappingStatus'); method=after.get('matchMethod')
            if status=='MATCHED_UNIQUE':
                if method not in ALLOWED_METHODS: raise RuntimeError(f'non-frozen unique mapping method accepted: {method}')
                if not after.get('mappedTicker') or not after.get('mappedSecurityId'): raise RuntimeError('unique mapping lacks ticker/security identity')
            elif method is not None and method not in ALLOWED_METHODS:
                raise RuntimeError(f'non-frozen mapping method present: {method}')


def main() -> None:
    holdings_run_id=int(os.environ['HOLDINGS_RUN_ID']); holdings_artifact_id=int(os.environ['HOLDINGS_ARTIFACT_ID'])
    npx_run_id=int(os.environ['NPX_PIT_RUN_ID']); npx_artifact_id=int(os.environ['NPX_PIT_ARTIFACT_ID'])
    if min(holdings_run_id,holdings_artifact_id,npx_run_id,npx_artifact_id)<=0: raise RuntimeError('fixed run/artifact lineage required')
    holdings=json.loads(HOLDINGS.read_text()); observed=validate_holdings_lineage(holdings)
    audit=json.loads(NPX_AUDIT.read_text())
    monthly_masters={month:json.loads(master_path(month).read_text()) for month,_ in EXPECTED_DATES}
    validate_npx(audit,monthly_masters)
    mapper=load_module('frozen_h1_2006_structural_mapper',ROOT/'scripts/research-nq-catalog-structural-mapping-h1-2006.py')
    TMP.mkdir(parents=True,exist_ok=True)
    mapped_snapshots=[]; per_month=[]; combined_methods=Counter(); input_by_month={s['signalMonth']:s for s in holdings['monthSnapshots']}
    counts={m:c for m,_,c in observed}
    for month,as_of in EXPECTED_DATES:
        input_snap=input_by_month[month]; raw_path=TMP/f'holdings-{month}.json'; map_path=TMP/f'mapping-{month}.json'
        raw_path.write_text(json.dumps({**holdings,'monthSnapshots':[input_snap]},indent=2)+'\n')
        mapper.RAW=raw_path; mapper.NPX=master_path(month); mapper.OUT=map_path; mapper.main()
        result=json.loads(map_path.read_text())
        if len(result.get('monthSnapshots',[]))!=1: raise RuntimeError(f'frozen mapper did not return one snapshot for {month}')
        mapped=result['monthSnapshots'][0]; validate_mapped_month(input_snap,mapped)
        if mapped['sourceSeriesCount']!=counts[month]: raise RuntimeError(f'unexpected source-Series count after mapping for {month}')
        mapped_snapshots.append(mapped); combined_methods.update(result.get('matchMethodCounts',{}))
        per_month.append({'signalMonth':month,'asOf':as_of,'sourceSeriesCount':counts[month],'npxMasterSha256':sha256(master_path(month)),'npxMasterRecordCount':len(monthly_masters[month].get('records',[])),'uniqueMappedCount':mapped.get('uniqueMappedCount'),'uniqueMappedCountRate':mapped.get('uniqueMappedCountRate'),'uniqueMappedWeightRate':mapped.get('uniqueMappedWeightRate'),'ambiguousCount':mapped.get('ambiguousCount'),'unmappedCount':mapped.get('unmappedCount'),'rejectedMasterIdentities':result.get('rejectedMasterIdentities')})
        print('H1_2008_MAPPING_MONTH',json.dumps(per_month[-1]),flush=True)
    out={'purpose':'H1 2008 deterministic structural mapping using frozen H1-2006 mapper and matching PIT N-PX master per signal month; no future repair, fuzzy matching, or outcome tuning.','validationDefinition':'docs/research/h1-2008-downstream-period-extension-validation-definition.md','sourceCatalogArtifactId':SOURCE_ARTIFACT_ID,'sourceCatalogSha256':SOURCE_SHA,'holdingsRunId':holdings_run_id,'holdingsArtifactId':holdings_artifact_id,'npxPitRunId':npx_run_id,'npxPitArtifactId':npx_artifact_id,'npxPitAuditSha256':sha256(NPX_AUDIT),'npxBaseArtifactId':NPX_BASE_ARTIFACT_ID,'mappingImplementationBlob':MAPPING_BLOB,'mappingRule':'Frozen baseline exact normalized issuer; unique ADR base; exact accepted structural suffix cleanup; >=20-character prefix only when candidate identity union is exactly one.','matchMethodCounts':dict(combined_methods),'monthlyNpxLineage':per_month,'monthSnapshots':mapped_snapshots}
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('H1_2008_MAPPING_SUMMARY',json.dumps({'months':len(mapped_snapshots),'sourceCatalogSha256':SOURCE_SHA,'holdingsRunId':holdings_run_id,'holdingsArtifactId':holdings_artifact_id,'npxPitRunId':npx_run_id,'npxPitArtifactId':npx_artifact_id,'matchMethodCounts':dict(combined_methods)}),flush=True)

if __name__=='__main__': main()
