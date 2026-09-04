#!/usr/bin/env python3
from __future__ import annotations
import html,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-historical-etf-issuer-own-evidence-pilot-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
# Validation labels are fund-structure labels only, not strategy outcomes.
SAMPLES=[
 {'label':'SELECT_SECTOR','expected':'ETF','filename':'edgar/data/1064641/0001193125-06-015013.txt'},
 {'label':'RYDEX_ETF_TRUST','expected':'ETF','filename':'edgar/data/1208211/0001193125-06-040623.txt'},
 {'label':'ISHARES_TRUST','expected':'ETF','filename':'edgar/data/1100663/0001193125-05-248361.txt'},
 {'label':'BUFFALO_FUNDS','expected':'CONVENTIONAL','filename':'edgar/data/1135300/0001104659-05-035519.txt'},
 {'label':'VICTORY_INSTITUTIONAL','expected':'CONVENTIONAL','filename':'edgar/data/1289876/0001193125-06-039508.txt'},
 {'label':'CONESTOGA','expected':'CONVENTIONAL','filename':'edgar/data/1175813/0000950152-06-000866.txt'},
 {'label':'UTOPIA','expected':'CONVENTIONAL','filename':'edgar/data/1335395/0001162044-05-001338.txt'},
]
# Positive creation language must describe the filing's own Fund/Portfolio/Shares as issuer/redemption actor.
CREATION=[
 re.compile(r'(?is)\b(?:each|the|a)\s+(?:[A-Z][A-Za-z&.\- ]{0,80}\s+)?(?:fund|portfolio)\b.{0,180}?\b(?:issues?|sells?|offers?)\s+and\s+redeems?\b.{0,260}?\bshares?\b.{0,300}?\bcreation\s+units?\b'),
 re.compile(r'(?is)\b(?:each|the|a)\s+(?:[A-Z][A-Za-z&.\- ]{0,80}\s+)?(?:fund|portfolio)\b.{0,180}?\b(?:issues?|sells?|offers?|redeems?)\b.{0,220}?\bshares?\b.{0,220}?\bcreation\s+units?\b'),
 re.compile(r'(?is)\b(?:ETF|VIPER)\s+shares?\b.{0,250}?\b(?:issued|redeemed|purchase|redemption)\b.{0,250}?\bcreation\s+units?\b'),
 re.compile(r'(?is)\bshares?\b.{0,160}?\b(?:issued|redeemed)\b.{0,220}?\bcreation\s+units?\b'),
]
# Positive exchange language must describe the Fund's/Shares' own secondary-market listing or trading.
EXCHANGE=[
 re.compile(r'(?is)\b(?:the\s+)?shares?\s+of\s+(?:each|the|a)\s+(?:[A-Z][A-Za-z&.\- ]{0,80}\s+)?(?:fund|portfolio)\b.{0,220}?\b(?:are|will\s+be)\s+(?:listed|traded)\b.{0,220}?\b(?:exchange|amex|nyse|nasdaq)\b'),
 re.compile(r'(?is)\b(?:each|the|a)\s+(?:[A-Z][A-Za-z&.\- ]{0,80}\s+)?(?:fund|portfolio)\b.{0,220}?\bshares?\b.{0,180}?\b(?:are|will\s+be)\s+(?:listed|traded)\b.{0,220}?\b(?:exchange|amex|nyse|nasdaq)\b'),
 re.compile(r'(?is)\bthe\s+shares?\b.{0,180}?\b(?:are|will\s+be)\s+(?:listed|traded)\b.{0,220}?\b(?:exchange|amex|nyse|nasdaq)\b'),
 re.compile(r'(?is)\b(?:ETF|VIPER)\s+shares?\b.{0,220}?\b(?:listed|traded)\b.{0,220}?\b(?:exchange|amex|nyse|nasdaq)\b'),
]
EXCLUSION_CONTEXT=re.compile(r'(?is)(?:investment\s+in|investments?\s+in|purchase\s+and\s+sell|underlying)\s+(?:other\s+investment\s+companies|ETFs?|exchange[- ]traded\s+funds?)')
SPACE=re.compile(r'\s+')
def fetch(fn):
 url='https://www.sec.gov/Archives/'+fn
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=25) as r:return r.read(4_000_000).decode('latin-1','replace'),url
def find(patterns,text):
 for p in patterns:
  for m in p.finditer(text):
   ctx=text[max(0,m.start()-500):min(len(text),m.end()+500)]
   # Reject matches embedded in a disclosure about investments in other ETFs.
   if EXCLUSION_CONTEXT.search(ctx):continue
   return m
 return None
def sn(text,m,r=260):
 if not m:return None
 return SPACE.sub(' ',html.unescape(text[max(0,m.start()-r):min(len(text),m.end()+r)])).strip()
def main():
 results=[]
 for s in SAMPLES:
  try:
   text,url=fetch(s['filename']);c=find(CREATION,text);e=find(EXCHANGE,text);pred='ETF' if c and e else 'NOT_ETF_EVIDENCE'
   r={**s,'submissionUrl':url,'creationIssuerOwnEvidence':bool(c),'exchangeIssuerOwnEvidence':bool(e),'prediction':pred,'creationSnippet':sn(text,c),'exchangeSnippet':sn(text,e)}
  except Exception as ex:r={**s,'prediction':'ERROR','error':type(ex).__name__}
  results.append(r);print('SAMPLE',json.dumps({k:r.get(k) for k in ('label','expected','creationIssuerOwnEvidence','exchangeIssuerOwnEvidence','prediction','error')}),flush=True)
 correct=sum((r['expected']=='ETF' and r['prediction']=='ETF') or (r['expected']=='CONVENTIONAL' and r['prediction']!='ETF') for r in results)
 out={'purpose':'Validation of a stricter historical ETF operational evidence grammar after the broad registrant prefilter produced conventional-fund false positives. Positive requires issuer-own Fund/Portfolio share issuance/redemption in Creation Units plus issuer-own share exchange listing/trading. Matches embedded in disclosures about investing in other ETFs are rejected. Labels are fund-structure validation only; no holdings outcomes, ranks, returns, or strategy results are used.','sampleCount':len(results),'correctCount':correct,'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({'sampleCount':len(results),'correctCount':correct}),flush=True)
if __name__=='__main__':main()
