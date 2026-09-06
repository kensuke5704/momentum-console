#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/research/sec-hybrid-etf-source-catalog-h1-2006.json'
FILENAME='edgar/data/1100663/0001193125-05-239024.txt'
ZERO={
'LEGACY:0001100663:3616BFF89723','LEGACY:0001100663:3EA7E8357EAF','LEGACY:0001100663:5A373E90FBA2',
'S000004335','S000004342','S000004343','S000004344','S000004346','S000004347','S000004439'}

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return m

hy=load('hy',ROOT/'scripts/research-nq-pit-holdings-hybrid-h1-2006.py')
g=load('g',ROOT/'scripts/research-nq-hybrid-grouping-v29.py')
p=load('p',ROOT/'scripts/research-nq-schedule-bound-parser-v29-v2.py')

def main():
    cat=json.loads(CAT.read_text())
    rows={}
    for snap in cat['monthSnapshots']:
        for src in snap['sourceFilings']:
            if src['filename']==FILENAME:
                rows[src['canonicalIdentity']]=src
    legacy={iid:r for iid,r in rows.items() if r['identityRegime']=='LEGACY_PRE_ID'}
    sub,transport,attempts=hy.fetch_submission(FILENAME)
    primary,desc,text,doctype=hy.h2diag.primary_document(sub,'N-CSRS')
    grouped,audit=g.legacy_grouped_schedule_blocks(text,legacy)
    parsed=[]
    for iid,row in sorted(legacy.items(), key=lambda kv: kv[1]['normalizedSeriesName']):
        blocks=grouped.get(iid,[]); combined='\n'.join(blocks); trimmed=p.corrected.trim_series_schedule(combined)
        html=p.base.parse_bound_html_holdings(trimmed)
        plain=p.parse_bound_plain_holdings(trimmed)
        method,final,total=p.parsed_holdings(combined)
        rec={'identity':iid,'seriesName':row['seriesName'],'zeroExpected':iid in ZERO,'blockCount':len(blocks),'combinedChars':len(combined),'trimmedChars':len(trimmed),'htmlCount':len(html),'plainCount':len(plain),'finalCount':len(final),'finalMethod':method,'total':total}
        parsed.append(rec); print('RESULT',json.dumps(rec),flush=True)
        if iid in ZERO:
            lines=p.pilot.plain_lines(combined)
            useful=[]
            for n,line in enumerate(lines):
                s=' '.join(line.split())
                if not s: continue
                if len(useful)<120:
                    useful.append({'n':n,'text':s[:260]})
            print('LINES_BEGIN',iid,flush=True)
            for x in useful: print(json.dumps(x),flush=True)
            print('LINES_END',iid,flush=True)
    # Print one successful peer for grammar contrast.
    peer=next((x for x in parsed if not x['zeroExpected'] and x['finalCount']>20),None)
    print('PEER',json.dumps(peer),flush=True)

if __name__=='__main__': main()
