#!/usr/bin/env python3
"""Append only the validated H2-2008 suffix to the immutable 30-month prefix."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data/research'
PREFIX=DATA/'historical-universe-builder-through-h1-2008.json'; SUFFIX=DATA/'historical-universe-builder-h2-2008.json'; VALIDATION=DATA/'h2-2008-downstream-period-extension-validation.json'; OUT=DATA/'historical-universe-builder-through-h2-2008.json'
BUILDER='1357402f34dfea1c1dbdcaac7de5078b680eb5c3'; SOURCE_SHA='ed76ca73a204302f660aba4e79573766b9aa4ef9a25837db7f9843cd980ec110'

def main():
    prefix=json.loads(PREFIX.read_text()); suffix=json.loads(SUFFIX.read_text()); validation=json.loads(VALIDATION.read_text())
    assert prefix.get('builderGitBlob')==BUILDER and suffix.get('builderGitBlob')==BUILDER
    assert validation.get('passed') is True and validation.get('sourceCatalogSha256')==SOURCE_SHA
    required=('parserInvariancePassed','mappingLineageFrozen','countryLineageFrozen','countryNoLookahead','corpBridgeMaterialityInvariant','frozenBuilderExactParitySixOfSix','top80RankInvariant')
    assert all(validation.get('checks',{}).get(k) is True for k in required)
    pre=prefix['monthSnapshots']; suf=suffix['monthSnapshots']
    months=[f'2006-{m:02d}' for m in range(1,13)]+[f'2007-{m:02d}' for m in range(1,13)]+[f'2008-{m:02d}' for m in range(1,13)]
    assert [x.get('signalMonth') for x in pre]==months[:30] and [x.get('signalMonth') for x in suf]==months[30:] and len(pre)==30 and len(suf)==6
    for key in ('eligibilityOrder','sourceEligibility','breadthRule'): assert prefix.get(key)==suffix.get(key)
    rows=pre+suf; assert [x.get('signalMonth') for x in rows]==months and len({x.get('signalMonth') for x in rows})==36 and all(len(x.get('symbols',[]))<=80 for x in rows)
    out={'purpose':'Immutable 36-month historical-Universe stitch through H2 2008. Copies the closed 30-month prefix verbatim and appends only the independently downstream-validated H2 2008 frozen-builder suffix; no reconstruction or strategy performance is run.','definition':'docs/research/h2-2008-36-month-stitch-validation-definition.md','builderGitBlob':BUILDER,'segments':[{'period':'2006-01..2008-06','runId':34354891519,'artifactId':10105279657,'artifactDigest':'sha256:98b33c37a2c25413d1d180b9b54d54d38fea1013e6b7c29af2f7cafea6d81d85','validation':'immutable closed 30-month prefix'},{'period':'2008-07..2008-12','runId':34437984621,'artifactId':10136871496,'artifactDigest':'sha256:55285c67440abb520da0b2e7b35dff88baf108a5f0976f453d6be0f2379fe7a3','sourceCatalogSha256':SOURCE_SHA,'validation':'H2 2008 downstream exact parity PASS'}],'eligibilityOrder':prefix.get('eligibilityOrder'),'sourceEligibility':prefix.get('sourceEligibility'),'breadthRule':prefix.get('breadthRule'),'monthSnapshots':rows}
    OUT.write_text(json.dumps(out,indent=2)+'\n'); check=json.loads(OUT.read_text()); assert check['monthSnapshots'][:30]==pre and check['monthSnapshots'][30:]==suf
if __name__=='__main__': main()
