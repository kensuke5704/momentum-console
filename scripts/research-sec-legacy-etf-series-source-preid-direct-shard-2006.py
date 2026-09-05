#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('base_preid',ROOT/'scripts'/'research-sec-legacy-etf-series-source-preid-shard-2006.py')
base=importlib.util.module_from_spec(SPEC);assert SPEC.loader;SPEC.loader.exec_module(base)
CLASS_TOKEN=re.compile(r'\b(?:VIPER(?:S)?|ETF|EXCHANGE[- ]TRADED)\b',re.I)
CLASS_ONLY=re.compile(r'^(?:VIPER(?:S)?(?: SHARES?)?|ETF SHARES?|EXCHANGE[- ]TRADED SHARES?)\s*[\*\(\)/®R.-]*$',re.I)

def direct_classify(title,normalized_title,registrant,op_index):
    norm_lines=op_index['normLines'];n=len(norm_lines);direct=[]
    for i in range(n):
        for width in (1,2,3):
            if i+width>n:continue
            phrase=' '.join(norm_lines[i:i+width]);pos=phrase.find(normalized_title)
            if pos<0:continue
            suffix=phrase[pos+len(normalized_title):].strip()
            if suffix and CLASS_TOKEN.search(suffix):
                direct.append((i,'TITLE_PHRASE_CARRIES_CLASS'))
            if phrase==normalized_title:
                j=i+width
                if j<n and CLASS_ONLY.fullmatch(norm_lines[j].strip()):
                    direct.append((i,'IMMEDIATE_CLASS_ONLY_LINE'))
    if not direct:return None,None
    markers=op_index['markerLines'];nearest=min((abs(i-j) for i,_ in direct for j in markers),default=0)
    if base.strict.TITLE_ETF_SEMANTIC.search(title):return 'TITLE_EXPLICIT_ETF_SEMANTIC',nearest
    if base.strict.REGISTRANT_ETF_SEMANTIC.search(registrant):return 'REGISTRANT_EXPLICIT_ETF_SEMANTIC',nearest
    return 'DIRECT_EXPLICIT_ETF_CLASS_ASSOCIATION',nearest

base.classify_binding_indexed=direct_classify
if __name__=='__main__':base.main()
