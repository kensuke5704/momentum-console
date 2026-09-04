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
 abs_urls=re.findall(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/[^\s\"\'<>\)]+',text,re.I)
 rel_urls=re.findall(r'(?<![A-Za-z0-9])(/Archives/edgar/data/[^\s\"\'<>\)]+)',text,re.I)
 out={'url':url,'transport':tr,'absoluteArchiveUrlCount':len(set(abs_urls)),'relativeArchiveUrlCount':len(set(rel_urls)),'absoluteArchiveUrls':list(dict.fromkeys(abs_urls))[:20],'relativeArchiveUrls':list(dict.fromkeys(rel_urls))[:20],'diagnosticLines':lines}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps(out),flush=True)
if __name__=='__main__':main()
