#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/research/sec-hybrid-etf-source-catalog-h1-2006.json'
F='edgar/data/1100663/0001193125-05-239024.txt'
TARGET={'S000004344','S000004439'}
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return m
hy=load('hy',ROOT/'scripts/research-nq-pit-holdings-hybrid-h1-2006-v29final-v3.py').hybrid
g=load('g2',ROOT/'scripts/research-nq-hybrid-grouping-v29-v2.py')
p=load('pv3',ROOT/'scripts/research-nq-pit-holdings-hybrid-h1-2006-v29final-v3.py').parser

def main():
 d=json.loads(CAT.read_text()); src={}
 for snap in d['monthSnapshots']:
  for x in snap['sourceFilings']:
   if x['filename']==F and x['canonicalIdentity'] in TARGET: src[x['canonicalIdentity']]=x
 sub,_,_=hy.fetch_submission(F); primary,_,text,_=hy.h2diag.primary_document(sub,'N-CSRS')
 series=[{'seriesId':iid,'seriesName':x['seriesName']} for iid,x in src.items()]
 grouped,audit=g.series_grouped_schedule_blocks(text,series)
 for iid,x in sorted(src.items()):
  blocks=grouped.get(iid,[]); combined='\n'.join(blocks); trimmed=p.corrected.trim_series_schedule(combined)
  html=p.base.parse_bound_html_holdings(trimmed); plain=p.parse_bound_plain_holdings(trimmed); method,final,total=hy.corrected.parsed_holdings(combined)
  print('RESULT',json.dumps({'identity':iid,'seriesName':x['seriesName'],'blockCount':len(blocks),'chars':len(combined),'htmlCount':len(html),'plainCount':len(plain),'finalCount':len(final),'method':method,'total':total}),flush=True)
  lines=p.pilot.plain_lines(combined)
  print('LINES_BEGIN',iid,flush=True)
  for n,line in enumerate(lines[:180]):
   s=' '.join(line.split())
   if s: print(json.dumps({'n':n,'text':s[:300]}),flush=True)
  print('LINES_END',iid,flush=True)
 print('ASSIGN',json.dumps([a for a in audit if a.get('seriesId') in TARGET],indent=2),flush=True)
if __name__=='__main__': main()
