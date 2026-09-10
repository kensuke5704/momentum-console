#!/usr/bin/env python3
"""Mechanical H2-2008 wrapper around the frozen H1-2006 structural mapper."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
DATES=[('2008-07','2008-07-31'),('2008-08','2008-08-29'),('2008-09','2008-09-30'),('2008-10','2008-10-31'),('2008-11','2008-11-28'),('2008-12','2008-12-31')]
SOURCE_ARTIFACT=10131298181
MAPPING_BLOB='690479017fc82dce2480ded5d1ffafbb76721722'
ALLOWED={'BASELINE_EXACT','BASELINE_ADR_BASE_UNIQUE','STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'}

def load():
    p=ROOT/'scripts/research-nq-series-id-structural-mapping-h1-2008.py'
    s=importlib.util.spec_from_file_location('h1_mapping_wrapper',p); m=importlib.util.module_from_spec(s); assert s.loader; s.loader.exec_module(m); return m

def main():
    m=load(); holdings=json.loads((DATA/'nq-pit-holdings-series-id-h2-2008.json').read_text())
    source_sha=holdings.get('sourceCatalogSha256')
    if not source_sha: raise RuntimeError('missing fixed H2 source content digest')
    def holdings_lineage(x):
        if x.get('sourceCatalogArtifactId')!=SOURCE_ARTIFACT or x.get('sourceCatalogSha256')!=source_sha: raise RuntimeError('unexpected H2 holdings source lineage')
        observed=[(s.get('signalMonth'),s.get('asOf'),s.get('catalogSourceSeriesCount')) for s in x.get('monthSnapshots',[])]
        if [(a,b) for a,b,_ in observed]!=DATES: raise RuntimeError(f'unexpected H2 holdings month boundary: {observed}')
        return observed
    def npx_path(month): return DATA/f'npx-pit-master-h2-2008-{month}.json'
    def npx_lineage(audit,monthly):
        if audit.get('status')!='PASS' or audit.get('fetchErrorCount') or audit.get('violations'): raise RuntimeError('H2 PIT N-PX audit is not clean')
        if audit.get('baseRunId')!=34320224950 or audit.get('baseArtifactId')!=10091573844: raise RuntimeError('unexpected H1 base lineage')
        if [(x.get('signalMonth'),x.get('asOf')) for x in audit.get('monthly',[])]!=DATES: raise RuntimeError('wrong H2 PIT months')
        for month,asof in DATES:
            master=monthly[month]
            if (master.get('signalMonth'),master.get('asOf'))!=(month,asof): raise RuntimeError('wrong PIT master assignment')
            if master.get('baseRunId')!=34320224950 or master.get('baseArtifactId')!=10091573844: raise RuntimeError('wrong PIT base lineage')
            for row in master.get('records',[]):
                filed=row.get('sourceFilingDate'); admitted=row.get('admittedAtSignal')
                if isinstance(filed,str) and filed.startswith('2008-') and filed>asof: raise RuntimeError('N-PX filing lookahead')
                if isinstance(admitted,str) and admitted>asof: raise RuntimeError('N-PX admission lookahead')
    m.HOLDINGS=DATA/'nq-pit-holdings-series-id-h2-2008.json'; m.NPX_AUDIT=DATA/'npx-pit-master-h2-2008-audit.json'
    m.OUT=DATA/'nq-series-id-structural-mapping-h2-2008.json'; m.TMP=DATA/'h2-2008-mapping-tmp'
    m.SOURCE_ARTIFACT_ID=SOURCE_ARTIFACT; m.SOURCE_SHA=source_sha; m.NPX_BASE_ARTIFACT_ID=10091573844; m.EXPECTED_DATES=DATES
    m.master_path=npx_path; m.validate_holdings_lineage=holdings_lineage; m.validate_npx=npx_lineage
    m.main()
    out=json.loads(m.OUT.read_text()); out['purpose']='H2 2008 deterministic structural mapping using frozen H1-2006 mapper and matching PIT N-PX master per signal month; no future repair, fuzzy matching, or outcome tuning.'
    out['validationDefinition']='docs/research/h2-2008-downstream-period-extension-validation-definition.md'; out['sourceCatalogArtifactId']=SOURCE_ARTIFACT; out['sourceCatalogSha256']=source_sha
    out['npxBaseArtifactId']=10091573844; out['mappingImplementationBlob']=MAPPING_BLOB
    if set(out.get('matchMethodCounts',{}))-ALLOWED: raise RuntimeError('non-frozen mapping method')
    m.OUT.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__': main()
