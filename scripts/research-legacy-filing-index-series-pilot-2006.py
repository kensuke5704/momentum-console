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
SID_RE=re.compile(r'\b(S\d{9})\b',re.I)
CID_RE=re.compile(r'\b(C\d{9})\b',re.I)
TICKER_RE=re.compile(r'^[A-Z][A-Z0-9.\-]{0,9}$')

def after_markdown_link(line:str, ident:str)->str:
 m=re.search(rf'\[{re.escape(ident)}\]\([^\)]+\)(.*)$',line,re.I)
 if m:return ' '.join(m.group(1).split())
 pos=line.upper().find(ident.upper())
 return ' '.join(line[pos+len(ident):].lstrip(' ]()').split()) if pos>=0 else ''
def get(url):
 last=None
 for u in (url,'https://r.jina.ai/'+url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=20).read().decode('utf-8','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')
def main():
 rows=[]
 for label,cik,acc in FILINGS:
  compact=acc.replace('-','');url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index.html';text,tr=get(url)
  lines=[x.strip() for x in text.splitlines() if x.strip()]
  pairs=[]
  for i,line in enumerate(lines):
   if 'Series' not in line:continue
   sm=SID_RE.search(line)
   if not sm:continue
   sid=sm.group(1).upper();sname=after_markdown_link(line,sid)
   for nxt in lines[i+1:i+5]:
    if 'Class/Contract' not in nxt:continue
    cm=CID_RE.search(nxt)
    if not cm:continue
    cid=cm.group(1).upper();tail=after_markdown_link(nxt,cid)
    toks=tail.split();ticker=toks[-1].upper() if toks and TICKER_RE.fullmatch(toks[-1].upper()) else ''
    cname=' '.join(toks[:-1]) if ticker else tail
    if ticker:pairs.append({'seriesId':sid,'classId':cid,'seriesName':sname,'className':cname,'ticker':ticker})
    break
  dedup=[];seen=set()
  for p in pairs:
   k=(p['seriesId'],p['classId'],p['ticker'])
   if k not in seen:seen.add(k);dedup.append(p)
  r={'label':label,'cik':cik,'accession':acc,'indexUrl':url,'transport':tr,'seriesClassTickerCount':len(dedup),'pairs':dedup};rows.append(r);print('FILING',json.dumps({k:v for k,v in r.items() if k!='pairs'}),flush=True)
  for p in dedup:print('PAIR',json.dumps({'label':label,**p}),flush=True)
 all_series=sorted({p['seriesId'] for r in rows for p in r['pairs']});all_tickers=sorted({p['ticker'] for r in rows for p in r['pairs']})
 out={'purpose':'Production-independent metadata pilot: extract historical registered series/class/ticker from SEC filing index pages for the three frozen 2006 N-Q source submissions. Native SEC filing index is preferred; r.jina is transport fallback only. No holdings content, ranks, or returns used.','filingCount':len(rows),'totalUniqueSeries':len(all_series),'totalUniqueTickers':len(all_tickers),'seriesIds':all_series,'tickers':all_tickers,'filings':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='filings'}),flush=True)
if __name__=='__main__':main()
