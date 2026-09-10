#!/usr/bin/env python3
"""H1-2008/H2-2008 parser-invariance audit using the frozen comparison logic."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'

def main():
    p=ROOT/'scripts/research-nq-holdings-parser-invariance-h2-2007-h1-2008.py'
    s=importlib.util.spec_from_file_location('frozen_parser_invariance',p); m=importlib.util.module_from_spec(s); assert s.loader; s.loader.exec_module(m)
    m.LEFT_HOLDINGS=DATA/'nq-pit-holdings-series-id-h1-2008.json'; m.RIGHT_HOLDINGS=DATA/'nq-pit-holdings-series-id-h2-2008.json'
    m.LEFT_SOURCE=DATA/'sec-id-era-strict-series-source-h1-2008.json'; m.RIGHT_SOURCE=DATA/'sec-id-era-strict-series-source-h2-2008.json'
    m.OUT=DATA/'nq-holdings-parser-invariance-h1-h2-2008.json'; m.main()
    out=json.loads(m.OUT.read_text()); out.update({'purpose':'Parser-invariance audit across validated H1-2008 and H2-2008 Series-ID raw holdings, using the frozen comparison implementation. Shared Series-ID + accession + SEC source-file keys must preserve parser-derived semantics, excluding only legacyIdentity schema metadata.','leftPeriod':'H1-2008','rightPeriod':'H2-2008','leftSourceArtifactId':10088832684,'rightSourceArtifactId':10131298181,'leftHoldingsArtifactId':10091627801,'rightHoldingsArtifactId':10131779818})
    m.OUT.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__': main()
