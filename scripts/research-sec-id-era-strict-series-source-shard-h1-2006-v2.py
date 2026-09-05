#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m

base=load('idv1',ROOT/'scripts/research-sec-id-era-strict-series-source-shard-h1-2006.py')
ETF_CLASS=re.compile(r'\b(?:ETF\s+SHARES?|VIPER(?:\s+SHARES?)?|EXCHANGE[- ]TRADED(?:\s+SHARES?)?)\b',re.I)
TITLE_ETF=re.compile(r'\b(?:ETF|SPDR|ISHARES|STREETTRACKS|VIPER)\b',re.I)
REGISTRANT_ETF=re.compile(r'\b(?:ETF|EXCHANGE[- ]TRADED)\b',re.I)

def bind_series_v2(series,registrant,lines,series_count):
    if any(ETF_CLASS.search(c.get('className') or '') for c in series.get('classes',[])):
        return 'EXPLICIT_ETF_CLASS_METADATA',0
    if TITLE_ETF.search(series.get('seriesName') or ''):
        return 'SERIES_TITLE_EXPLICIT_ETF_SEMANTIC',None
    if REGISTRANT_ETF.search(registrant or ''):
        return 'REGISTRANT_EXPLICIT_ETF_SEMANTIC',None
    if series_count==1:
        return 'SINGLE_SERIES_FILING_WITH_ISSUER_OWN_EVIDENCE',None
    return None,None

base.bind_series=bind_series_v2
if __name__=='__main__':base.main()
