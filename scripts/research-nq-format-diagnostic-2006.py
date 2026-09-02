#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IDX=ROOT/'data'/'research'/'nq-index-2006.json'
spec=importlib.util.spec_from_file_location('meta',ROOT/'scripts'/'research-nq-series-metadata-2006.py');meta=importlib.util.module_from_spec(spec);spec.loader.exec_module(meta)
TARGET=re.compile(r'POWERSHARES EXCHANGE TRADED FUND TRUST',re.I)
SCHEDULE=re.compile(r'SCHEDULE OF PORTFOLIO INVESTMENTS|SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS',re.I)
def clean(s): return ' '.join(re.sub(r'(?is)<[^>]+>',' ',s).split())
def main():
 d=json.loads(IDX.read_text()); seen=set()
 for x in d['filings']:
  if x.get('form')!='N-Q' or not TARGET.search(x.get('company','')) or x['cik'] in seen: continue
  seen.add(x['cik']); _,text=meta.fetch_prefix(meta.sec_url(x['filename'])); markers=list(SCHEDULE.finditer(text))
  for j,m in enumerate(markers):
   ctx=clean(text[m.start():min(len(text),m.start()+1800)])
   if 'PowerShares Dynamic Market Portfolio' not in ctx: continue
   end=markers[j+1].start() if j+1<len(markers) else min(len(text),m.start()+250000)
   chosen=text[m.start():end]
   print('RAW_REPR',repr(chosen[:12000]),flush=True)
   for needle in ('<td','&lt;td','<TD','&lt;TD','Number of Shares','Market Value'):
    print('NEEDLE',needle,'count',chosen.count(needle),'first',chosen.find(needle),flush=True)
   break
  break
if __name__=='__main__': main()
