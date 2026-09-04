#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-browse-link-diagnostic-intc-2006.json'
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)

def main():
 url=old.sec_url({'action':'getcompany','CIK':'0000050863','type':'10-K','dateb':'20060228','owner':'exclude','count':'10'})
 text,tr=old.get(url,timeout=20)
 lines=[x.strip() for x in text.splitlines() if '/Archives/edgar/data/' in x or '10-K' in x][:80]
 abs_urls=list(dict.fromkeys(re.findall(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/[^\s\"\'<>\)]+',text,re.I)))
 rel_urls=list(dict.fromkeys(re.findall(r'(?<![A-Za-z0-9])(/Archives/edgar/data/[^\s\"\'<>\)]+)',text,re.I)))
 idx_diag=[]
 if abs_urls:
  try:
   idx_text,idx_tr=old.get(abs_urls[0],timeout=20)
   state_lines=[x.strip() for x in idx_text.splitlines() if re.search(r'State\s+of\s+Incorp|STATE.OF.INCORPORATION|INTEL CORP|CIK',x,re.I)][:40]
   idx_diag={'url':abs_urls[0],'transport':idx_tr,'stateLines':state_lines,'rawStateMatches':re.findall(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)[^\r\n]{0,80}',idx_text,re.I)[:20]}
  except Exception as e:idx_diag={'error':repr(e)}
 out={'url':url,'transport':tr,'absoluteArchiveUrlCount':len(abs_urls),'relativeArchiveUrlCount':len(rel_urls),'absoluteArchiveUrls':abs_urls[:20],'relativeArchiveUrls':rel_urls[:20],'diagnosticLines':lines,'firstIndexDiagnostic':idx_diag}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps(out),flush=True)
if __name__=='__main__':main()
