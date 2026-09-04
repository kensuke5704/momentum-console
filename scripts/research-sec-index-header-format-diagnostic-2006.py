#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-index-header-format-diagnostic-2006.json'
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)
HEADER_URL='https://www.sec.gov/Archives/edgar/data/70858/000119312505039878/0001193125-05-039878-index-headers.html'
SUBMISSION_URL='https://www.sec.gov/Archives/edgar/data/70858/0001193125-05-039878.txt'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}

def native(url,headers=None,limit=200000,timeout=8):
 req=urllib.request.Request(url,headers=headers or UA)
 with urllib.request.urlopen(req,timeout=timeout) as r:
  return r.read(limit).decode('latin-1','replace'),getattr(r,'status',None),dict(r.headers.items())

def main():
 try:head_native,head_status,head_headers=native(HEADER_URL)
 except Exception as e:head_native='';head_status=None;head_headers={};head_error=repr(e)
 else:head_error=None
 head_relay,head_tr=old.get(HEADER_URL,timeout=12)
 range_headers={**UA,'Range':'bytes=0-32767'}
 try:raw,raw_status,raw_headers=native(SUBMISSION_URL,range_headers,32768,10)
 except Exception as e:raw='';raw_status=None;raw_headers={};raw_error=repr(e)
 else:raw_error=None
 markers=['COMPANY DATA','COMPANY CONFORMED NAME','CENTRAL INDEX KEY','STATE OF INCORPORATION','CONFORMED-NAME','STATE-OF-INCORPORATION','BANK OF AMERICA','0000070858','<SEC-HEADER>','<COMPANY-DATA>']
 out={
  'purpose':'Transport/format-only diagnostic for one preselected 2005 SEC filing. No holdings, returns, ranks or strategy outcomes are used.',
  'headerUrl':HEADER_URL,'headerNativeStatus':head_status,'headerNativeError':head_error,'headerNativeLength':len(head_native),
  'headerRelayTransport':head_tr,'headerRelayLength':len(head_relay),
  'headerRelayMarkers':{m:(m.lower() in head_relay.lower()) for m in markers},
  'submissionUrl':SUBMISSION_URL,'submissionStatus':raw_status,'submissionError':raw_error,'submissionLength':len(raw),
  'submissionContentRange':raw_headers.get('Content-Range'),'submissionContentLength':raw_headers.get('Content-Length'),
  'submissionMarkers':{m:(m.lower() in raw.lower()) for m in markers},
  'headerRelayExcerpt':head_relay[:3000],
  'submissionExcerpt':raw[:12000]
 }
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in out.items() if not k.endswith('Excerpt')}),flush=True)
if __name__=='__main__':main()
