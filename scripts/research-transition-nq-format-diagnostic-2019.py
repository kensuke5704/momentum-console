#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-nq-format-diagnostic-2019.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
SAMPLES=[
 ('SKYY','https://www.sec.gov/Archives/edgar/data/1364608/000144554619001205/etf2_nq.htm'),
 ('FTXL','https://www.sec.gov/Archives/edgar/data/1552740/000144554619001208/etf6_nq.htm'),
 ('HACK','https://www.sec.gov/Archives/edgar/data/1467831/000089418919001075/etfmg_nq.htm'),
 ('CWS','https://www.sec.gov/Archives/edgar/data/1408970/000161577418012797/s113544_nq.htm'),
]
def get(url):
 req=urllib.request.Request('https://r.jina.ai/'+url,headers=UA)
 with urllib.request.urlopen(req,timeout=60) as r:return r.read(4_000_000).decode('utf-8','replace')
def main():
 rows=[]
 for label,url in SAMPLES:
  text=get(url);lines=text.splitlines()
  table=[x for x in lines if x.count('|')>=3]
  numeric=[x for x in table if re.search(r'\d[\d,]*(?:\.\d+)?',x)]
  schedule=[i for i,x in enumerate(lines) if re.search(r'SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS',x,re.I)]
  examples=[]
  for i in schedule[:3]:examples.extend(lines[max(0,i-3):min(len(lines),i+30)])
  if not examples:examples=numeric[:60]
  rec={'label':label,'url':url,'chars':len(text),'lines':len(lines),'pipeTableLines':len(table),'numericPipeLines':len(numeric),'scheduleMarkers':len(schedule),'examples':examples[:100]}
  rows.append(rec);print('FORMAT',label,json.dumps({k:v for k,v in rec.items() if k!='examples'}),flush=True)
  for x in rec['examples'][:20]:print(label,repr(x[:260]),flush=True)
 out={'purpose':'Structural rendering diagnostic only. Used to define parser grammar; no Universe ranking or strategy outcomes used.','rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
