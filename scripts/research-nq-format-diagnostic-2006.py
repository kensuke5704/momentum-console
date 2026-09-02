#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IDX=ROOT/'data'/'research'/'nq-index-2006.json'
spec=importlib.util.spec_from_file_location('meta',ROOT/'scripts'/'research-nq-series-metadata-2006.py');meta=importlib.util.module_from_spec(spec);spec.loader.exec_module(meta)
TARGET=re.compile(r'POWERSHARES EXCHANGE TRADED FUND TRUST|PROSHARES TRUST',re.I)
SCHEDULE=re.compile(r'SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS',re.I)
def clean(s): return ' '.join(re.sub(r'(?is)<[^>]+>',' ',s).split())
def main():
 d=json.loads(IDX.read_text()); rows=[]; seen=set()
 for x in d['filings']:
  if x.get('form')!='N-Q' or not TARGET.search(x.get('company','')) or x['cik'] in seen: continue
  seen.add(x['cik']); rows.append(x)
 for x in rows:
  _,text=meta.fetch_prefix(meta.sec_url(x['filename'])); series=[s for s in meta.parse_series_contracts(text,x['company']) if s['isEtf']]
  print('FILE',x['company'],x['dateFiled'],x['filename'],'bytes',len(text),'series',len(series),flush=True)
  for i,m in enumerate(list(SCHEDULE.finditer(text))[:20],1):
   lo=max(0,m.start()-1200); hi=min(len(text),m.start()+1800)
   print('SCHEDULE_CONTEXT',i,clean(text[lo:hi])[:2400],flush=True)
  print('SERIES_BODY_HITS',flush=True)
  for s in series:
   name=s.get('seriesName') or ''
   toks=[re.escape(t) for t in re.sub(r'[^A-Z0-9]+',' ',name.upper()).split() if len(t)>1]
   if not toks: continue
   pat=re.compile(r'\b'+r'\W+'.join(toks)+r'\b',re.I); hits=list(pat.finditer(text))
   snippets=[]
   for h in hits[-3:]: snippets.append(clean(text[max(0,h.start()-250):min(len(text),h.end()+700)])[:850])
   print(json.dumps({'name':name,'ticker':s.get('etfTickers',[]),'hits':len(hits),'tailContexts':snippets}),flush=True)
if __name__=='__main__': main()
