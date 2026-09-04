#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)
def idx(doc):
 m=ARCH_RE.search(doc)
 if not m:return None
 cik,compact=m.group(1),m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}'
 return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index.html'
def main():
 seed=[x for x in cur.CM.get('INTC',[]) if x.get('normalizedTitle')==cur.old.normalize_name('Intel Corp.')][0]
 b=cur.old.browse_cik(seed['cik'],'2005-12-31')
 urls=[]
 for d in b.get('archiveUrls',[]):
  u=idx(d)
  if u and u not in urls:urls.append(u)
 print('BROWSE',json.dumps({'seed':seed,'archiveUrls':b.get('archiveUrls',[])[:8],'indexUrls':urls[:8]}),flush=True)
 for u in urls[:4]:
  try:text,tr=cur.old.get(u,timeout=15)
  except Exception as e:
   print('ERR',u,type(e).__name__,flush=True);continue
  lines=[x.strip() for x in text.splitlines() if re.search(r'State|Incorp|INTEL|CIK',x,re.I)]
  print('INDEX',json.dumps({'url':u,'transport':tr,'lines':lines[:30]}),flush=True)
if __name__=='__main__':main()
