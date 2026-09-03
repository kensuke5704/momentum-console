#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
URL='https://www.sec.gov/Archives/edgar/data/1467831/000089418919008202/etfmg_n-csr.htm'
TARGETS=['S000047480','S000050191','S000053021']
def get(url):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=45) as r:raw=r.read(6_000_000)
   return raw.decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.5)
 raise last
def first(filings):
 d={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  if f.get('seriesId') and f['seriesId'] not in d:d[f['seriesId']]=f
 return d
with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
filings=b.get('snapshots',b) if isinstance(b,dict) else b;fs=first(filings)
text,tr=get(URL);ls=text.splitlines();print('TRANSPORT',tr,'CHARS',len(text),'LINES',len(ls))
for sid in TARGETS:
 name=fs[sid].get('seriesName') or fs[sid].get('fundName') or sid
 print('\n===== SERIES',sid,name,'=====')
 hits=[i for i,x in enumerate(ls) if name.lower() in x.lower()]
 print('NAME_HITS',hits[:20])
 for i in hits[:3]:
  print('---NAME CONTEXT',i,'---')
  for j in range(max(0,i-25),min(len(ls),i+120)):
   if any(k in ls[j].lower() for k in ['common stock','schedule of investments','portfolio of investments','shares','value']) or abs(j-i)<=15:
    print(f'{j:06d}: {ls[j][:500]}')
# Global headings give the exact rendering grammar without looking at NPORT overlap.
print('\n===== GLOBAL COMMON STOCK CONTEXTS =====')
for i,x in enumerate(ls):
 if re.search(r'COMMON STOCK',x,re.I):
  print('---COMMON',i,'---')
  for j in range(max(0,i-8),min(len(ls),i+35)):print(f'{j:06d}: {ls[j][:500]}')
  if i>5000:break
