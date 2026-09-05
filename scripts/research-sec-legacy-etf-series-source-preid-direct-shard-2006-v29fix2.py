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
    norm_lines=op_index['normLines'];n=len(norm_lines);parts=normalized_title.split()
    if not parts:return None,None
    exact_hits=set();direct=[];seen=set()
    for token_line in op_index['tokenLines'].get(parts[0],()):
        for i in range(max(0,token_line-2),token_line+1):
            for width in (1,2,3):
                if i+width>n or not (i<=token_line<i+width):continue
                key=(i,width)
                if key in seen:continue
                seen.add(key)
                phrase=base.phrase_norm(op_index,i,width)
                if base.accepted_title_phrase(phrase,normalized_title):exact_hits.add(i)
                pos=phrase.find(normalized_title)
                if pos<0:continue
                suffix=phrase[pos+len(normalized_title):].strip()
                # A trailing class token is direct only when title and class text
                # occur on the same original normalized line. Multi-line phrase
                # concatenation can cross a Series boundary in mixed trusts.
                if width==1 and suffix and CLASS_TOKEN.search(suffix):direct.append((i,'TITLE_LINE_CARRIES_CLASS'))
                if phrase==normalized_title:
                    j=i+width
                    if j<n and CLASS_ONLY.fullmatch(norm_lines[j].strip()):direct.append((i,'IMMEDIATE_CLASS_ONLY_LINE'))
    if not exact_hits:return None,None
    markers=op_index['markerLines']
    nearest_exact=min((abs(i-j) for i in exact_hits for j in markers),default=None)
    if base.strict.TITLE_ETF_SEMANTIC.search(title):return 'TITLE_EXPLICIT_ETF_SEMANTIC',nearest_exact
    if base.strict.REGISTRANT_ETF_SEMANTIC.search(registrant):return 'REGISTRANT_EXPLICIT_ETF_SEMANTIC',nearest_exact
    if not direct:return None,nearest_exact
    nearest_direct=min((abs(i-j) for i,_ in direct for j in markers),default=nearest_exact)
    return 'DIRECT_EXPLICIT_ETF_CLASS_ASSOCIATION',nearest_direct

base.classify_binding_indexed=direct_classify
if __name__=='__main__':base.main()
