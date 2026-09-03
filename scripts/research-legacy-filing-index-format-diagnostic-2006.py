#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/legacy-filing-index-format-diagnostic-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com'}
FILINGS=[('SELECT_SECTOR','1064641','0000950135-06-001225'),('RYDEX_ETF','1208211','0000950135-06-001815'),('STREETTRACKS','1064642','0000950135-06-003650')]
def get(url):
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=20).read().decode('utf-8','replace'),u
  except Exception:pass
 raise RuntimeError('fetch failed')
def main():
 rows=[]
 for label,cik,acc in FILINGS:
  url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}/{acc}-index.html';text,tr=get(url); lines=text.splitlines(); hits=[]
  for i,line in enumerate(lines):
   if re.search(r'Series|Class/Contract|Ticker|S\d{9}|C\d{9}',line,re.I):
    hits.append({'line':i+1,'text':line[:500],'context':'\n'.join(lines[max(0,i-2):min(len(lines),i+5)])[:2500]})
  r={'label':label,'url':url,'transport':tr,'length':len(text),'hitCount':len(hits),'hits':hits[:80]};rows.append(r)
  print('FILING',json.dumps({k:v for k,v in r.items() if k!='hits'}),flush=True)
  for h in hits[:30]:print('HIT',json.dumps({'label':label,**h}),flush=True)
 out={'purpose':'Inspect actual text/markdown grammar around Series/Class/Ticker metadata on fixed 2006 SEC filing index pages. Diagnostic only.','filings':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
