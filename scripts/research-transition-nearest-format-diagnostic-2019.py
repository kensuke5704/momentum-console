#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.request,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/research/transition-nearest-format-diagnostic-2019.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com'}
SAMPLES=[
('FPX','First Trust US Equity Opportunities ETF','https://www.sec.gov/Archives/edgar/data/1329377/000144554619003838/etf1_ncsrs.txt'),
('SKYY','First Trust Cloud Computing ETF','https://www.sec.gov/Archives/edgar/data/1364608/000144554619005018/etf2_ncsr.txt'),
('AIRR','First Trust RBA American Industrial Renaissance ETF','https://www.sec.gov/Archives/edgar/data/1552740/000144554619005047/etf6_ncsr.htm'),
('HACK','ETFMG Prime Cyber Security ETF','https://www.sec.gov/Archives/edgar/data/1467831/000089418918004455/etfmg_nq.htm'),
('CWS','AdvisorShares Focused Equity ETF','https://www.sec.gov/Archives/edgar/data/1408970/000161577419003003/s115583_ncsrs.htm'),
]
def get(url):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=60) as r:return r.read(6_000_000).decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.5)
 raise last
def main():
 rows=[]
 for label,title,url in SAMPLES:
  try:text,tr=get(url)
  except Exception as e:rows.append({'label':label,'error':repr(e)});continue
  ls=text.splitlines();hits=[i for i,x in enumerate(ls) if title.lower() in x.lower()]
  windows=[]
  for i in hits[:3]:
   windows.extend([{'line':j,'text':ls[j][:500]} for j in range(max(0,i-10),min(len(ls),i+120))])
  rec={'label':label,'title':title,'url':url,'transport':tr,'chars':len(text),'lines':len(ls),'titleHits':hits[:10],'windows':windows}
  rows.append(rec);print('DOC',label,'chars',len(text),'hits',hits[:5],flush=True)
  for x in windows[:80]:print(label,x['line'],repr(x['text']),flush=True)
 out={'purpose':'Structural parser diagnostic only for nearest legacy reports; no holdings overlap or strategy outcomes used.','rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
