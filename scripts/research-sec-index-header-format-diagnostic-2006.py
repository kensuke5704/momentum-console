#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-index-header-format-diagnostic-2006.json'
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)
URL='https://www.sec.gov/Archives/edgar/data/70858/000119312505039878/0001193125-05-039878-index-headers.html'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}

def main():
 native_error=None
 try:
  req=urllib.request.Request(URL,headers=UA)
  with urllib.request.urlopen(req,timeout=8) as r:native=r.read(200000).decode('latin-1','replace');native_status=getattr(r,'status',None)
 except Exception as e:
  native='';native_status=None;native_error=repr(e)
 relay,tr=old.get(URL,timeout=12)
 markers=['COMPANY DATA','COMPANY CONFORMED NAME','CENTRAL INDEX KEY','STATE OF INCORPORATION','BANK OF AMERICA','0000070858']
 out={
  'purpose':'Transport/format-only diagnostic for one preselected 2005 SEC filing header. No holdings, returns, ranks or strategy outcomes are used.',
  'url':URL,'nativeStatus':native_status,'nativeError':native_error,'nativeLength':len(native),
  'relayTransport':tr,'relayLength':len(relay),
  'nativeMarkers':{m:(m.lower() in native.lower()) for m in markers},
  'relayMarkers':{m:(m.lower() in relay.lower()) for m in markers},
  'relayCompanyDataPositions':[m.start() for m in re.finditer('company data',relay,re.I)][:5],
  'relayExcerpt':relay[:7000]
 }
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='relayExcerpt'}),flush=True)
if __name__=='__main__':main()
