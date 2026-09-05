#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-zero-marker-heading-diagnostic-h2-2005.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
FILINGS=[
 {'cik':'0000862084','company':'VANGUARD INSTITUTIONAL INDEX FUND','form':'N-CSRS','dateFiled':'2005-08-25','filename':'edgar/data/862084/0000932471-05-001228.txt'},
 {'cik':'0001091462','company':'HUNTINGTON VA FUNDS','form':'N-CSR/A','dateFiled':'2005-09-08','filename':'edgar/data/1091462/0001318148-05-000511.txt'},
 {'cik':'0000734383','company':'VANGUARD SPECIALIZED FUNDS','form':'N-CSRS','dateFiled':'2005-09-29','filename':'edgar/data/734383/0000932471-05-001568.txt'},
 {'cik':'0000857489','company':'VANGUARD INTERNATIONAL EQUITY INDEX FUNDS','form':'N-CSR','dateFiled':'2005-12-27','filename':'edgar/data/857489/0000932471-05-001803.txt'},
]
DOC=re.compile(r'(?is)<DOCUMENT>(.*?)</DOCUMENT>'); TYPE=re.compile(r'(?im)^\s*<TYPE>\s*([^\s<]+)'); TEXT=re.compile(r'(?is)<TEXT>(.*)</TEXT>')
KEY=re.compile(r'(?i)\b(?:INVEST(?:MENT|MENTS|ING)?|PORTFOLIO|NET\s+ASSETS?|SECURIT(?:Y|IES)|HOLDINGS?)\b')

def fetch(fn):
 url='https://www.sec.gov/Archives/'+fn
 errs=[]
 for u in (url,'https://r.jina.ai/'+url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=35) as r:return r.read(25_000_000).decode('latin-1','replace'),u
  except Exception as e:errs.append(type(e).__name__)
 raise RuntimeError(','.join(errs))

def primary(sub,form):
 base=form.replace('/A','').upper(); fallback=None
 for m in DOC.finditer(sub):
  b=m.group(1); tm=TYPE.search(b); typ=tm.group(1).strip().upper() if tm else ''
  tx=TEXT.search(b); raw=tx.group(1) if tx else b
  if typ==form.upper(): return raw,typ
  if typ.replace('/A','')==base and fallback is None:fallback=(raw,typ)
 return fallback or (sub,'')

def lines(raw):
 s=re.sub(r'(?is)<(?:br|p|div|tr|td|th|li|h[1-6])\b[^>]*>','\n',raw)
 s=re.sub(r'(?is)</(?:p|div|tr|td|th|li|h[1-6])>','\n',s)
 s=re.sub(r'(?is)<[^>]+>',' ',s);s=html.unescape(s).replace('\xa0',' ')
 return [' '.join(x.split()) for x in s.splitlines() if ' '.join(x.split())]

def main():
 out=[]
 for f in FILINGS:
  rec=dict(f)
  try:
   sub,tr=fetch(f['filename']);raw,typ=primary(sub,f['form']);ls=lines(raw); hits=[]
   for i,line in enumerate(ls):
    if KEY.search(line):
     # headings/short structural lines only; avoid dumping portfolio rows
     if len(line)<=180:
      hits.append({'lineIndex':i,'line':line,'before':ls[max(0,i-2):i],'after':ls[i+1:i+3]})
   rec.update({'transport':tr,'primaryDocumentType':typ,'lineCount':len(ls),'headingCandidateCount':len(hits),'headingCandidates':hits[:500]})
  except Exception as e:rec.update({'error':type(e).__name__,'errorDetail':str(e)[:500]})
  out.append(rec);print('FILING',json.dumps({'company':f['company'],'form':f['form'],'hits':rec.get('headingCandidateCount'),'error':rec.get('error')}),flush=True)
 doc={'purpose':'Diagnose exact complete-portfolio heading grammar for the four H2 2005 candidate filings that produced zero markers under the accepted schedule-heading regex. Output is limited to short lines containing investment/portfolio/net-assets/securities/holdings terms and adjacent lines. No holdings outcomes, later Series IDs, ranks, returns, or strategy results are used.','filingCount':len(out),'results':out}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(doc,indent=2)+'\n');print('SUMMARY',json.dumps({'filingCount':len(out),'errors':sum('error' in x for x in out)}),flush=True)
if __name__=='__main__':main()
