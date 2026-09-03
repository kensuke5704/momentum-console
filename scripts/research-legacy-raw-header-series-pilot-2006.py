#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/legacy-raw-header-series-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com'}
FILINGS=[
 ('SELECT_SECTOR','1064641','0000950135-06-001225'),
 ('RYDEX_ETF','1208211','0000950135-06-001815'),
 ('STREETTRACKS','1064642','0000950135-06-003650'),
]
SID_RE=re.compile(r'\b(S\d{9})\b',re.I)
CID_RE=re.compile(r'\b(C\d{9})\b',re.I)
TICKER_TAG_RE=re.compile(r'<(?:TICKER|CLASS-CONTRACT-TICKER-SYMBOL)>\s*([^\n\r<]+)',re.I)
SERIES_BLOCK_RE=re.compile(r'<SERIES>(.*?)(?=<SERIES>|</SERIES-AND-CLASSES-CONTRACTS-DATA>|\Z)',re.I|re.S)

def get(url):
 last=None
 for u in (url,'https://r.jina.ai/'+url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=20).read().decode('utf-8','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')
def urls(cik,acc):
 ad=acc.replace('-','');base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{ad}/'
 return [base+acc+'.hdr.sgml',base+acc+'.txt',base+acc+'-index-headers.html']
def parse(text):
 pairs=[]
 for block in SERIES_BLOCK_RE.findall(text):
  sm=SID_RE.search(block)
  if not sm:continue
  sid=sm.group(1).upper()
  # one series can have multiple class/contracts
  cids=list(dict.fromkeys(x.upper() for x in CID_RE.findall(block)))
  ticks=[m.group(1).strip().upper() for m in TICKER_TAG_RE.finditer(block)]
  for i,cid in enumerate(cids):
   ticker=ticks[i] if i<len(ticks) else (ticks[0] if len(ticks)==1 else '')
   pairs.append({'seriesId':sid,'classId':cid,'ticker':ticker})
 # broad fallback: capture raw IDs even if exact SGML blocks differ
 if not pairs:
  sids=list(dict.fromkeys(x.upper() for x in SID_RE.findall(text)))
  cids=list(dict.fromkeys(x.upper() for x in CID_RE.findall(text)))
  ticks=[m.group(1).strip().upper() for m in TICKER_TAG_RE.finditer(text)]
  for i,sid in enumerate(sids):pairs.append({'seriesId':sid,'classId':cids[i] if i<len(cids) else '', 'ticker':ticks[i] if i<len(ticks) else ''})
 return pairs

def main():
 rows=[]
 for label,cik,acc in FILINGS:
  attempts=[];best=[]
  for u in urls(cik,acc):
   try:
    text,tr=get(u);pairs=parse(text);attempts.append({'url':u,'transport':tr,'length':len(text),'seriesIdCount':len(set(p['seriesId'] for p in pairs)),'pairCount':len(pairs)})
    if len(pairs)>len(best):best=pairs
   except Exception as e:attempts.append({'url':u,'error':type(e).__name__})
  r={'label':label,'cik':cik,'accession':acc,'seriesClassTickerCount':len(best),'pairs':best,'attempts':attempts};rows.append(r)
  print('FILING',json.dumps({k:v for k,v in r.items() if k!='pairs'}),flush=True)
  for p in best:print('PAIR',json.dumps({'label':label,**p}),flush=True)
 all_series=sorted({p['seriesId'] for r in rows for p in r['pairs']});all_tickers=sorted({p['ticker'] for r in rows for p in r['pairs'] if p['ticker']})
 out={'purpose':'Production-independent 2006 source-discovery transport pilot: test raw SEC filing header resources for registered Series/Class/Ticker metadata on the three frozen N-Q filings. No holdings content, ranks, or returns used.','filingCount':len(rows),'totalUniqueSeries':len(all_series),'totalUniqueTickers':len(all_tickers),'seriesIds':all_series,'tickers':all_tickers,'filings':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='filings'}),flush=True)
if __name__=='__main__':main()
