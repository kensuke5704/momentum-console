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
SERIES_RE=re.compile(r'Series\s+(S\d{9})\s*.*?\|?\s*([^\r\n<]+)',re.I)
PAIR_RE=re.compile(r'Series\s+(S\d{9}).*?Class/Contract\s+(C\d{9}).*?\|\s*([^\r\n<|]+?)\s*\|\s*([A-Z][A-Z0-9.\-]{0,9})\b',re.I|re.S)

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
  pairs=[]
  for m in PAIR_RE.finditer(text):pairs.append({'seriesId':m.group(1).upper(),'classId':m.group(2).upper(),'name':' '.join(m.group(3).split()),'ticker':m.group(4).upper()})
  # r.jina markdown fallback: parse line blocks around Series/Class rows.
  if not pairs:
   lines=[x.strip() for x in text.splitlines()]
   for i,line in enumerate(lines):
    sm=re.search(r'Series\s+(S\d{9})',line,re.I)
    if not sm:continue
    sid=sm.group(1).upper();window='\n'.join(lines[i:i+8]);cm=re.search(r'Class/Contract\s+(C\d{9})',window,re.I);tm=re.search(r'\|\s*([A-Z][A-Z0-9.\-]{0,9})\s*$',window,re.M)
    name=''
    # capture likely series name from same/next line after series id.
    after=re.sub(r'^.*?Series\s+S\d{9}\s*','',line,flags=re.I).strip(' |')
    if after:name=after
    if cm and tm:pairs.append({'seriesId':sid,'classId':cm.group(1).upper(),'name':name,'ticker':tm.group(1).upper()})
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
