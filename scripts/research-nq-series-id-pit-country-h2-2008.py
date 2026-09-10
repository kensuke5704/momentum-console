#!/usr/bin/env python3
"""Mechanical H2-2008 continuation of the frozen strict PIT country resolver."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'

def main():
    p=ROOT/'scripts/research-nq-series-id-pit-country-h1-2008.py'
    s=importlib.util.spec_from_file_location('h1_country_extension',p); m=importlib.util.module_from_spec(s); assert s.loader; s.loader.exec_module(m)
    mapping=DATA/'nq-series-id-structural-mapping-h2-2008.json'
    lineage=json.loads(mapping.read_text())
    source_sha=lineage.get('sourceCatalogSha256')
    if not source_sha or len(source_sha)!=64: raise RuntimeError('missing fixed H2 source content digest')
    if lineage.get('sourceCatalogArtifactId')!=10131298181: raise RuntimeError('unexpected H2 source artifact')
    m.MAPPING=mapping; m.NPX=DATA/'npx-pit-master-h2-2008-2008-12.json'
    m.SHARDS=DATA/'series-id-country-h2-2008-shards'
    m.COUNTRY_OUT=DATA/'nq-series-id-country-pit-h2-2008.json'
    m.DIAGNOSTIC_OUT=DATA/'nq-series-id-country-extension-diagnostic-h2-2008.json'
    m.NPX_BASE_ARTIFACT_ID=10091573844
    os.environ['SOURCE_CATALOG_SHA256']=source_sha
    m.main()

if __name__=='__main__': main()
