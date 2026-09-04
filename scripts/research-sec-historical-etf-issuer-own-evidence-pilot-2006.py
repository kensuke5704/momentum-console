#!/usr/bin/env python3
from __future__ import annotations
import html,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-historical-etf-issuer-own-evidence-pilot-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
# Exact evidence filings are copied from the completed Q1 market-wide prefilter artifacts.
# Validation labels are fund-structure labels only, not strategy outcomes.
SAMPLES=[
 {'label':'SELECT_SECTOR','expected':'ETF','filename':'edgar/data/1064641/0000950135-06-000351.txt'},
 {'label':'RYDEX_ETF_TRUST','expected':'ETF','filename':'edgar/data/1208211/0000935069-06-000534.txt'},
 {'label':'ISHARES_TRUST','expected':'ETF','filename':'edgar/data/1100663/0001193125-05-243343.txt'},
 {'label':'BUFFALO_FUNDS','expected':'CONVENTIONAL','filename':'edgar/data/1135300/0000894189-05-001870.txt'},
 {'label':'VICTORY_INSTITUTIONAL','expected':'CONVENTIONAL','filename':'edgar/data/1289876/0001047469-06-002615.txt'},
 {'label':'CONESTOGA','expected':'CONVENTIONAL','filename':'edgar/data/1175813/0000922423-06-000120.txt'},
 {'label':'UTOPIA','expected':'CONVENTIONAL','filename':'edgar/data/1335395/0000950137-05-015448.txt'},
]
CREATION=[
 re.compile(r'(?is)\b(?:each|the|a)\s+(?:[A-Z][A-Za-z&.\- ]{0,80}\s+)?(?:fund|portfolio)\b.{0,180}?\b(?:issues?|sells?|offers?)\s+and\s+redeems?\b.{0,260}?\bshares?\b.{0,300}?\bcreation\s+units?\b'),
 re.compile(r'(?is)\b(?:each|the|a)\s+(?:[A-Z][A-Za-z&.\- ]{0,80}\s+)?(?:fund|portfolio)\b.{0,180}?\b(?:issues?|sells?|offers?|redeems?)\b.{0,220}?\bshares?\b.{0,220}?\bcreation\s+units?\b'),
 re.compile(r'(?is)\b(?:ETF|VIPER)\s+shares?\b.{0,250}?\b(?:issued|redeemed|purchase|redemption)\b.{0,250}?\bcreation\s+units?\b'),
 re.compile(r'(?is)\bshares?\b.{0,160}?\b(?:issued|redeemed)\b.{0,220}?\bcreation\s+units?\b'),
]
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
 errs=[]
 for u in (url,'https://r.jina.ai/'+url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=25) as r:return r.read(4_000_000).decode('latin-1','replace'),u,errs
  except Exception as e:errs.append({'transport':u,'error':type(e).__name__})
 raise RuntimeError(json.dumps(errs))
def find(patterns,text):
 for p in patterns:
  for m in p.finditer(text):
   ctx=text[max(0,m.start()-500):min(len(text),m.end()+500)]
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
   text,url,prior=fetch(s['filename']);c=find(CREATION,text);e=find(EXCHANGE,text);pred='ETF' if c and e else 'NOT_ETF_EVIDENCE'
   r={**s,'transport':url,'priorTransportErrors':prior,'creationIssuerOwnEvidence':bool(c),'exchangeIssuerOwnEvidence':bool(e),'prediction':pred,'creationSnippet':sn(text,c),'exchangeSnippet':sn(text,e)}
  except Exception as ex:r={**s,'prediction':'ERROR','error':type(ex).__name__}
  results.append(r);print('SAMPLE',json.dumps({k:r.get(k) for k in ('label','expected','creationIssuerOwnEvidence','exchangeIssuerOwnEvidence','prediction','error')}),flush=True)
 evaluable=[r for r in results if r['prediction']!='ERROR']
 correct=sum((r['expected']=='ETF' and r['prediction']=='ETF') or (r['expected']=='CONVENTIONAL' and r['prediction']=='NOT_ETF_EVIDENCE') for r in evaluable)
 out={'purpose':'Validation of a stricter historical ETF operational evidence grammar after the broad registrant prefilter produced conventional-fund false positives. Positive requires issuer-own Fund/Portfolio share issuance/redemption in Creation Units plus issuer-own share exchange listing/trading. Matches embedded in disclosures about investing in other ETFs are rejected. Exact evidence filings come from completed market-wide Q1 prefilter artifacts. Labels are fund-structure validation only; no holdings outcomes, ranks, returns, or strategy results are used.','sampleCount':len(results),'evaluableCount':len(evaluable),'correctCount':correct,'errorCount':len(results)-len(evaluable),'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
