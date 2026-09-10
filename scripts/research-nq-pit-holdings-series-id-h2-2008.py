#!/usr/bin/env python3
"""Mechanical H2-2008 path/SHA extension of the frozen H1 holdings wrapper."""
from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load():
    p=ROOT/'scripts/research-nq-pit-holdings-series-id-h1-2008.py'
    s=importlib.util.spec_from_file_location('h1_holdings_wrapper',p)
    m=importlib.util.module_from_spec(s); assert s.loader; s.loader.exec_module(m)
    return m

def main():
    m=load(); d=ROOT/'data/research'
    m.SOURCE=d/'sec-id-era-strict-series-source-h2-2008.json'
    m.ADAPTED=d/'sec-id-era-strict-series-source-h2-2008-holdings-adapter.json'
    m.OUT=d/'nq-pit-holdings-series-id-h2-2008.json'
    # The workflow pins the immutable source artifact by run, artifact name,
    # and artifact ZIP digest.  Its extracted JSON has a distinct content
    # digest; pass that exact digest through the otherwise frozen extractor.
    m.SOURCE_SHA=hashlib.sha256(m.SOURCE.read_bytes()).hexdigest()
    m.main()
    out=json.loads(m.OUT.read_text())
    out['purpose']=('H2 2008 Series-ID source-catalog-driven raw complete-portfolio holdings extraction. '
        'The frozen authoritative holdings extractor is reused unchanged; only the mechanical H2 source schema adapter and output path differ. '
        'Holdings content never determines source identity. No ticker, fuzzy matching, rank, return, or strategy outcome is used.')
    out['sourceCatalogPath']=str(m.SOURCE.relative_to(ROOT))
    out['schemaAdapterPath']=str(m.ADAPTED.relative_to(ROOT))
    m.OUT.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__': main()
