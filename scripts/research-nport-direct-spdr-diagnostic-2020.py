#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / 'nport-direct-spdr-diagnostic-2020.json'
UA = {'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'application/xml,text/xml,text/plain,*/*'}

FIXTURE = {
    'seriesId':'S000006415',
    'seriesName':'The Technology Select Sector SPDR Fund',
    'ticker':'XLK',
    'reportDate':'2020-03-31',
    'filingDate':'2020-06-01',
    'accession':'0001752724-20-111526',
    'url':'https://www.sec.gov/Archives/edgar/data/1064641/000175272420111526/primary_doc.xml',
}

def fetch(url: str):
    attempts=[]
    for label,u in [('sec-direct',url),('jina','https://r.jina.ai/http://' + url.removeprefix('https://'))]:
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=90) as r:
                b=r.read()
            text=b.decode('utf-8','replace')
            attempts.append({'transport':label,'ok':True,'bytes':len(b),'prefix':text[:500]})
            return label,text,attempts
        except Exception as e:
            attempts.append({'transport':label,'ok':False,'error':repr(e)})
    return None,'',attempts

def local_tag_counts(text: str):
    tags=re.findall(r'<(?:[A-Za-z0-9_.-]+:)?([A-Za-z0-9_.-]+)(?:\s|>)',text)
    out={}
    for t in tags: out[t]=out.get(t,0)+1
    return sorted(out.items(), key=lambda kv:(-kv[1],kv[0]))[:100]

transport,text,attempts=fetch(FIXTURE['url'])
out={
    'purpose':'Transport/schema diagnostic for one predeclared Select Sector SPDR 2020 N-PORT filing. Structural only; no prices/returns/ranks used.',
    'fixture':FIXTURE,
    'transport':transport,
    'attempts':attempts,
    'length':len(text),
    'looksXml':text.lstrip().startswith('<?xml') or '<edgarSubmission' in text or '<invstOrSec' in text,
    'invstOrSecCount':len(re.findall(r'<(?:[A-Za-z0-9_.-]+:)?invstOrSec(?:\s|>)',text,re.I)),
    'tagCounts':local_tag_counts(text),
    'sampleAroundInvestment':None,
}
m=re.search(r'<(?:[A-Za-z0-9_.-]+:)?invstOrSec(?:\s|>)',text,re.I)
if m: out['sampleAroundInvestment']=text[m.start():m.start()+5000]
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'tagCounts','sampleAroundInvestment','attempts'}},sort_keys=True))
print('ATTEMPTS',json.dumps(attempts,sort_keys=True))
print('TOP_TAGS',json.dumps(out['tagCounts'][:40]))
if out['sampleAroundInvestment']: print('SAMPLE',out['sampleAroundInvestment'][:3000])
if not transport: raise SystemExit(2)
