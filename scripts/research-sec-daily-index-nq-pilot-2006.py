#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-daily-index-nq-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com'}
DATES=[('2006','QTR1','20060228'),('2006','QTR2','20060531')]

def get(url):
 last=None
 for u in (url,'https://r.jina.ai/'+url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=25).read().decode('latin1','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')
def parse(text):
 rows=[]
 for line in text.splitlines():
  p=line.split('|')
  if len(p)==5 and p[2].strip().upper() in {'N-Q','N-Q/A'}:
   rows.append({'cik':p[0].strip(),'company':p[1].strip(),'form':p[2].strip(),'date':p[3].strip(),'path':p[4].strip()})
 return rows
def main():
 results=[]
 for y,q,d in DATES:
  url=f'https://www.sec.gov/Archives/edgar/daily-index/{y}/{q}/master.{d}.idx';text,tr=get(url);rows=parse(text)
  r={'date':d,'url':url,'transport':tr,'textBytes':len(text.encode("utf-8","ignore")),'nqCount':len(rows),'uniqueCiks':len({x['cik'] for x in rows}),'rows':rows};results.append(r);print('DAY',json.dumps({k:v for k,v in r.items() if k!='rows'}),flush=True)
  for x in rows[:20]:print('NQ',json.dumps(x),flush=True)
 out={'purpose':'Transport/source-discovery pilot using SEC daily master indexes instead of blocked quarterly master.zip. Only N-Q/N-Q-A filing metadata is extracted; no holdings, ranks or returns used.','days':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
