#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IDX=ROOT/'data'/'research'/'nq-index-2006.json'
spec=importlib.util.spec_from_file_location('meta',ROOT/'scripts'/'research-nq-series-metadata-2006.py');meta=importlib.util.module_from_spec(spec);spec.loader.exec_module(meta)
pspec=importlib.util.spec_from_file_location('pilot',ROOT/'scripts'/'research-nq-parser-pilot.py');pilot=importlib.util.module_from_spec(pspec);pspec.loader.exec_module(pilot)
TARGET=re.compile(r'POWERSHARES EXCHANGE TRADED FUND TRUST|PROSHARES TRUST',re.I)
SCHEDULE=re.compile(r'SCHEDULE OF PORTFOLIO INVESTMENTS|SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS',re.I)
def clean(s): return ' '.join(re.sub(r'(?is)<[^>]+>',' ',s).split())
def td_stream(text):
 parts=re.split(r'(?is)<TD\b[^>]*>',text)[1:]
 return [pilot.clean_cell(re.split(r'(?is)(?:</?TR\b[^>]*>|</?TABLE\b[^>]*>|<TD\b[^>]*>)',p,maxsplit=1)[0]) for p in parts]
def main():
 d=json.loads(IDX.read_text()); rows=[]; seen=set()
 for x in d['filings']:
  if x.get('form')!='N-Q' or not TARGET.search(x.get('company','')) or x['cik'] in seen: continue
  seen.add(x['cik']); rows.append(x)
 for x in rows:
  _,text=meta.fetch_prefix(meta.sec_url(x['filename'])); series=[s for s in meta.parse_series_contracts(text,x['company']) if s['isEtf']]
  markers=list(SCHEDULE.finditer(text))
  print('FILE',x['company'],x['dateFiled'],x['filename'],'bytes',len(text),'series',len(series),'markers',len(markers),flush=True)
  if x['company'].upper().startswith('POWERSHARES'):
   chosen=None
   for j,m in enumerate(markers):
    ctx=clean(text[m.start():min(len(text),m.start()+1800)])
    if 'PowerShares Dynamic Market Portfolio' in ctx:
     end=markers[j+1].start() if j+1<len(markers) else min(len(text),m.start()+250000)
     chosen=text[m.start():end]
     break
   if chosen:
    cells=[c for c in td_stream(chosen) if c]
    print('POWERSHARES_STREAM_CELLS',len(cells),flush=True)
    for k,c in enumerate(cells[:220]): print('CELL',k,json.dumps(c),flush=True)
    method,_,_,hold=pilot.parse_holdings(chosen)
    print('POWERSHARES_PARSE',method,len(hold),json.dumps(hold[:5]),flush=True)
  else:
   for i,m in enumerate(markers[:8],1):
    lo=max(0,m.start()-500); hi=min(len(text),m.start()+1000)
    print('SCHEDULE_CONTEXT',i,clean(text[lo:hi])[:1300],flush=True)
if __name__=='__main__': main()
