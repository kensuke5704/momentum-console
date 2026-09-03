#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/legacy-etf-identity-text-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com'}
# Positive sources are the frozen ETF N-Q submissions. Negative controls are deterministic ordinary fund filings from the prior master-index pilot.
CASES=[
 {'label':'ETF_SELECT_SECTOR','expected':'ETF','url':'https://www.sec.gov/Archives/edgar/data/1064641/000095013506001225/0000950135-06-001225.txt'},
 {'label':'ETF_RYDEX','expected':'ETF','url':'https://www.sec.gov/Archives/edgar/data/1208211/000095013506001815/0000950135-06-001815.txt'},
 {'label':'ETF_STREETTRACKS','expected':'ETF','url':'https://www.sec.gov/Archives/edgar/data/1064642/000095013506003650/0000950135-06-003650.txt'},
]
PATTERNS={
 'creation_unit':re.compile(r'\bcreation units?\b',re.I),
 'exchange_traded':re.compile(r'\bexchange[- ]traded\b',re.I),
 'stock_exchange':re.compile(r'\b(?:american|new york|national) stock exchange\b|\bNYSE\b|\bAMEX\b|\bNASDAQ\b',re.I),
 'secondary_market':re.compile(r'\bsecondary market\b',re.I),
 'depositary_receipt':re.compile(r'\bdepositary receipts?\b',re.I),
}
def get(url):
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=30).read(6_000_000).decode('utf-8','replace'),u
  except Exception:pass
 raise RuntimeError('fetch failed')
def main():
 rows=[]
 for c in CASES:
  text,tr=get(c['url']);hits={k:len(p.findall(text)) for k,p in PATTERNS.items()};snips={}
  for k,p in PATTERNS.items():
   m=p.search(text)
   if m:snips[k]=' '.join(text[max(0,m.start()-100):m.end()+180].split())[:360]
  r={**c,'transport':tr,'textLength':len(text),'hits':hits,'hasCreationUnit':hits['creation_unit']>0,'hasExchangeTraded':hits['exchange_traded']>0,'hasExchangeMarketSignal':hits['stock_exchange']>0 or hits['secondary_market']>0,'snippets':snips};rows.append(r);print('CASE',json.dumps({k:v for k,v in r.items() if k!='snippets'}),flush=True)
 out={'purpose':'Filing-time text pilot for legacy ETF identity. Tests explicit creation-unit/exchange-traded/secondary-market signals on the three frozen 2006 ETF source submissions; no holdings ranks or returns used.','rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
