#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/clearbridge-filing-date-2020.json'
BASE='https://www.sec.gov/Archives/edgar/data/1645194/000119312519202172/'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/html,text/plain,*/*'}

def fetch(url,range_n=None):
 headers=dict(UA)
 if range_n:headers['Range']=f'bytes=0-{range_n-1}'
 req=urllib.request.Request(url,headers=headers)
 with urllib.request.urlopen(req,timeout=30) as r:return r.read(range_n or 2_000_000).decode('utf-8','replace'),getattr(r,'status',None),dict(r.headers)

def parse_date(text):
 pats=[r'FILED AS OF DATE:\s*(\d{8})',r'FILING DATE\s*</[^>]+>\s*<[^>]+>\s*(\d{4}-\d{2}-\d{2})',r'Filing Date\s*(\d{4}-\d{2}-\d{2})']
 for p in pats:
  m=re.search(p,text,re.I|re.S)
  if m:
   x=m.group(1);return f'{x[:4]}-{x[4:6]}-{x[6:8]}' if re.fullmatch(r'\d{8}',x) else x
 return None

def main():
 attempts=[];date=None
 urls=[BASE+'0001193125-19-202172-index-headers.html',BASE+'0001193125-19-202172-index.htm']
 for u in urls:
  try:
   text,status,h=fetch(u);d=parse_date(text);attempts.append({'url':u,'status':status,'length':len(text),'date':d,'hits':[x.strip() for x in text.splitlines() if 'FILED AS OF DATE' in x or 'Filing Date' in x][:10]})
   if d:date=d;break
  except Exception as e:attempts.append({'url':u,'status':'ERROR','error':repr(e)})
 if not date:
  u=BASE+'0001193125-19-202172.txt'
  for n in (131072,262144,524288):
   try:
    text,status,h=fetch(u,n);d=parse_date(text);attempts.append({'url':u,'bytes':n,'status':status,'length':len(text),'contentRange':h.get('Content-Range'),'date':d,'hits':[x.strip() for x in text.splitlines() if 'FILED AS OF DATE' in x or 'ACCEPTANCE-DATETIME' in x][:10]})
    if d:date=d;break
   except Exception as e:attempts.append({'url':u,'bytes':n,'status':'ERROR','error':repr(e)})
 out={'accession':'0001193125-19-202172','filingDate':date,'attempts':attempts}
 print('RESULT',json.dumps(out),flush=True)
 if not date:raise RuntimeError('ClearBridge filing date unresolved; do not run aggregate scoring')
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
