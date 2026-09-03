#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/legacy-filing-index-series-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com'}
FILINGS=[
 ('SELECT_SECTOR','1064641','0000950135-06-001225'),
 ('RYDEX_ETF','1208211','0000950135-06-001815'),
 ('STREETTRACKS','1064642','0000950135-06-003650'),
]
SERIES_LINE_RE=re.compile(r'^Series\s+\[(S\d{9})\]\([^\)]*\)(.+?)\s*$',re.I)
CLASS_LINE_RE=re.compile(r'^Class/Contract\s+\[(C\d{9})\]\([^\)]*\)(.+?)\s+([A-Z][A-Z0-9.\-]{0,9})\s*$',re.I)

def get(url):
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=20).read().decode('utf-8','replace'),u
  except Exception:pass
 raise RuntimeError('fetch failed')
def main():
 rows=[]
 for label,cik,acc in FILINGS:
  compact=acc.replace('-','');url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index.html';text,tr=get(url)
  lines=[x.strip() for x in text.splitlines() if x.strip()]
  pairs=[]
  for i,line in enumerate(lines):
   sm=SERIES_LINE_RE.match(line)
   if not sm:continue
   sid=sm.group(1).upper();sname=' '.join(sm.group(2).split())
   # In SEC/r.jina index grammar the matching Class/Contract line immediately follows the Series line.
   for nxt in lines[i+1:i+4]:
    cm=CLASS_LINE_RE.match(nxt)
    if cm:
     cname=' '.join(cm.group(2).split());ticker=cm.group(3).upper()
     pairs.append({'seriesId':sid,'classId':cm.group(1).upper(),'seriesName':sname,'className':cname,'ticker':ticker})
     break
  dedup=[];seen=set()
  for p in pairs:
   k=(p['seriesId'],p['classId'],p['ticker'])
   if k not in seen:seen.add(k);dedup.append(p)
  r={'label':label,'cik':cik,'accession':acc,'indexUrl':url,'transport':tr,'seriesClassTickerCount':len(dedup),'pairs':dedup};rows.append(r);print('FILING',json.dumps({k:v for k,v in r.items() if k!='pairs'}),flush=True)
  for p in dedup:print('PAIR',json.dumps({'label':label,**p}),flush=True)
 all_series=sorted({p['seriesId'] for r in rows for p in r['pairs']});all_tickers=sorted({p['ticker'] for r in rows for p in r['pairs']})
 out={'purpose':'Production-independent metadata pilot: extract historical registered series/class/ticker from SEC filing index pages for the three frozen 2006 N-Q source submissions. No holdings content, ranks, or returns used.','filingCount':len(rows),'totalUniqueSeries':len(all_series),'totalUniqueTickers':len(all_tickers),'seriesIds':all_series,'tickers':all_tickers,'filings':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='filings'}),flush=True)
if __name__=='__main__':main()
