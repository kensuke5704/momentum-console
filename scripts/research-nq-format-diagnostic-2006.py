#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IDX=ROOT/'data'/'research'/'nq-index-2006.json'
spec=importlib.util.spec_from_file_location('meta',ROOT/'scripts'/'research-nq-series-metadata-2006.py');meta=importlib.util.module_from_spec(spec);spec.loader.exec_module(meta)
pspec=importlib.util.spec_from_file_location('pilot',ROOT/'scripts'/'research-nq-parser-pilot.py');pilot=importlib.util.module_from_spec(pspec);pspec.loader.exec_module(pilot)
TARGET=re.compile(r'POWERSHARES EXCHANGE TRADED FUND TRUST',re.I)
SCHEDULE=re.compile(r'SCHEDULE OF PORTFOLIO INVESTMENTS|SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS',re.I)
def clean(s): return ' '.join(re.sub(r'(?is)<[^>]+>',' ',s).split())
def main():
 d=json.loads(IDX.read_text()); seen=set()
 for x in d['filings']:
  if x.get('form')!='N-Q' or not TARGET.search(x.get('company','')) or x['cik'] in seen: continue
  seen.add(x['cik']); _,text=meta.fetch_prefix(meta.sec_url(x['filename'])); markers=list(SCHEDULE.finditer(text))
  for j,m in enumerate(markers):
   ctx=clean(text[m.start():min(len(text),m.start()+500)])
   if not re.search(r'Schedule of Investments\s+PowerShares Dynamic Market Portfolio',ctx,re.I): continue
   end=markers[j+1].start() if j+1<len(markers) else min(len(text),m.start()+250000)
   chosen=text[m.start():end]
   print('MARKER_INDEX',j+1,'CTX',ctx[:500],flush=True)
   print('RAW_REPR',repr(chosen[:5000]),flush=True)
   for needle in ('<td','</td>','<tr','</tr>','Number of Shares','Market Value'):
    print('NEEDLE',needle,'count',chosen.lower().count(needle.lower()),'first',chosen.lower().find(needle.lower()),flush=True)
   rows=pilot.html_rows(chosen)
   print('HTML_ROWS',len(rows),flush=True)
   for k,row in enumerate(rows[:25]): print('ROW',k,json.dumps(row),flush=True)
   method,_,_,hold=pilot.parse_holdings(chosen)
   print('PARSE',method,len(hold),json.dumps(hold[:8]),flush=True)
   break
  break
if __name__=='__main__': main()
