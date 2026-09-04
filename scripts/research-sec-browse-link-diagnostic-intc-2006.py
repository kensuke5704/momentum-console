#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-browse-link-diagnostic-intc-2006.json'
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)

def inspect(url,mode):
 target=url if mode=='native' else 'https://r.jina.ai/'+url
 try:
  req=urllib.request.Request(target,headers=old.UA)
  with urllib.request.urlopen(req,timeout=20) as r:text=r.read(2_000_000).decode('utf-8','replace')
  state_lines=[x.strip() for x in text.splitlines() if re.search(r'State\s+of\s+Incorp|STATE.OF.INCORPORATION|INTEL CORP|CIK',x,re.I)][:50]
  return {'target':target,'ok':True,'length':len(text),'stateLines':state_lines,'rawStateMatches':re.findall(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)[^\r\n<]{0,100}',text,re.I)[:20]}
 except Exception as e:return {'target':target,'ok':False,'error':repr(e)}
def main():
 url=old.sec_url({'action':'getcompany','CIK':'0000050863','type':'10-K','dateb':'20060228','owner':'exclude','count':'10'})
 text,tr=old.get(url,timeout=20)
 abs_urls=list(dict.fromkeys(re.findall(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/[^\s\"\'<>\)]+',text,re.I)))
 first=abs_urls[0] if abs_urls else ''
 variants=[]
 if first:
  urls=[first,first+'?output=1']
  if first.endswith('.htm'):urls.append(first[:-4]+'.html')
  for u in urls:
   for mode in ('native','jina'):variants.append(inspect(u,mode))
 out={'browseUrl':url,'browseTransport':tr,'firstIndexUrl':first,'variants':variants}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps(out),flush=True)
if __name__=='__main__':main()
