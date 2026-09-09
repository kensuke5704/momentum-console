#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import re
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,application/zip,*/*','Accept-Encoding':'identity'}
CORE={'485BPOS','485APOS','485BXT','N-1A','N-1A/A'};SUPP={'497'};FORMS=CORE|SUPP
SID_RE=re.compile(r'^S\d{9}$',re.I)
CUTOFF='2008-12-31'
_LAST_REQUEST_AT=0.0

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m

# Reuse the exact validated issuer-own operational grammar and corrected filing-index structural parser.
rule=load_module('issuer_rule',ROOT/'scripts/research-sec-historical-etf-issuer-own-evidence-pilot-2006.py')
idxp=load_module('idxp',ROOT/'scripts/research-sec-marketwide-series-class-shard-q1-2006.py')

def fb(url,limit=4_000_000,timeout=20):
    # SEC serves this research archive under a rate limit.  This is transport
    # hygiene only: callers still receive the identical document bytes and
    # parser/acceptance semantics are unchanged.
    global _LAST_REQUEST_AT
    delay=0.25-(time.monotonic()-_LAST_REQUEST_AT)
    if delay>0: time.sleep(delay)
    req=urllib.request.Request(url,headers=UA)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(limit),getattr(r,'status',None)
    finally:
        _LAST_REQUEST_AT=time.monotonic()

def ft(url,limit=1_500_000,timeout=18):
    errs=[]
    for attempt in range(1,4):
        for u in (url,'https://r.jina.ai/'+url):
            try:b,s=fb(u,limit,timeout);return b.decode('latin-1','replace'),u,s,errs
            except Exception as e:errs.append({'attempt':attempt,'transport':u,'error':type(e).__name__})
        if attempt<3: time.sleep(2*attempt)
    raise RuntimeError(json.dumps(errs))

def master(y,q):
    base=f'https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}';zu=base+'/master.zip'
    try:
        b,_=fb(zu,25_000_000,45)
        with zipfile.ZipFile(io.BytesIO(b)) as z:n=next(x for x in z.namelist() if x.lower().endswith('master.idx'));return z.read(n).decode('latin-1','replace'),zu
    except Exception:
        t,u,_,_=ft(base+'/master.idx',25_000_000,50);return t,u

def load_prospectus(ciks):
    by=defaultdict(list);trs={}
    for y,qs in ((2005,range(1,5)),(2006,range(1,5)),(2007,range(1,5)),(2008,range(1,5))):
        for q in qs:
            t,tr=master(y,q);trs[f'{y}Q{q}']=tr
            for ln in t.splitlines():
                p=ln.split('|')
                if len(p)<5 or not p[0].strip().isdigit():continue
                cik,co,form,date,fn=[x.strip() for x in p[:5]];cik=cik.zfill(10);form=form.upper()
                if cik in ciks and form in FORMS and date<=CUTOFF:by[cik].append({'cik':cik,'company':co,'form':form,'dateFiled':date,'filename':fn})
    return by,trs

def su(fn):return 'https://www.sec.gov/Archives/'+fn.lstrip('/')

def parse_index_series(url):
    text,tr,status,prior=ft(url,1_500_000,16)
    records=idxp.parse_markdown_records(text) if tr.startswith('https://r.jina.ai/') else idxp.parse_html_records(text)
    series=[];current=None
    for r in records:
        if r.get('type')=='series' and SID_RE.fullmatch(r.get('seriesId','')):
            current={'seriesId':r['seriesId'].upper(),'seriesName':r.get('seriesName','').strip(),'classes':[]};series.append(current)
        elif r.get('type')=='class' and current is not None:current['classes'].append({'classId':r.get('classId'),'className':r.get('className',''),'ticker':r.get('ticker','')})
    ded=[];seen=set()
    for s in series:
        if s['seriesId'] in seen:continue
        seen.add(s['seriesId']);ded.append(s)
    return ded,tr,prior
