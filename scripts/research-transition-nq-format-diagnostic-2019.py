#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-nq-format-diagnostic-2019.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
SAMPLES=[
 ('SKYY','First Trust Cloud Computing ETF','https://www.sec.gov/Archives/edgar/data/1364608/000144554619001205/etf2_nq.htm'),
 ('FTXL','First Trust Nasdaq Semiconductor ETF','https://www.sec.gov/Archives/edgar/data/1552740/000144554619001208/etf6_nq.htm'),
]
def get(url):
 last=None
 for attempt in range(4):
  try:
   req=urllib.request.Request('https://r.jina.ai/'+url,headers=UA)
   with urllib.request.urlopen(req,timeout=90) as r:return r.read(4_000_000).decode('utf-8','replace')
  except Exception as e:last=e;time.sleep(3*(attempt+1))
 raise last or RuntimeError('fetch failed')
def main():
 rows=[]
 for label,title,url in SAMPLES:
  text=get(url);lines=text.splitlines();normtitle=re.sub(r'[^A-Z0-9]+',' ',title.upper()).strip()
  hits=[]
  for i,x in enumerate(lines):
   nx=re.sub(r'[^A-Z0-9]+',' ',x.upper()).strip()
   if normtitle and normtitle in nx:hits.append(i)
  windows=[]
  for i in hits[:5]:
   for j in range(max(0,i-8),min(len(lines),i+140)):
    windows.append({'line':j,'text':lines[j][:500]})
  rec={'label':label,'title':title,'url':url,'chars':len(text),'lines':len(lines),'titleHits':hits[:20],'windows':windows[:500]}
  rows.append(rec);print('FORMAT',label,json.dumps({k:v for k,v in rec.items() if k!='windows'}),flush=True)
  for w in rec['windows'][:180]:print(label,w['line'],repr(w['text']),flush=True)
 out={'purpose':'Series-local structural rendering diagnostic only; no Universe ranking or strategy outcomes used.','rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
