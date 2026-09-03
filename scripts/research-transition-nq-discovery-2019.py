#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-nq-discovery-2019.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
# Fixed from exact same-series continuity evidence; independent of overlap/performance.
CIKS=[
 {'cik':'0001329377','label':'First Trust Exchange-Traded Fund'},
 {'cik':'0001364608','label':'First Trust Exchange-Traded Fund II'},
 {'cik':'0001552740','label':'First Trust Exchange-Traded Fund VI'},
 {'cik':'0001467831','label':'ETF Managers Trust'},
 {'cik':'0001408970','label':'AdvisorShares Trust'},
]
ARCHIVE_RE=re.compile(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"\'<>\)]+',re.I)
ACC_RE=re.compile(r'(\d{10}-\d{2}-\d{6})')
DATE_RE=re.compile(r'Filing Date\s*(\d{4}-\d{2}-\d{2})',re.I)

def get(url,timeout=20):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r: raw=r.read(3_000_000)
   return raw.decode('utf-8','replace'),u,len(raw)
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')

def browse(cik):
 q=urllib.parse.urlencode({'action':'getcompany','CIK':cik,'type':'N-Q','dateb':'20191231','owner':'exclude','count':'100'})
 url='https://www.sec.gov/cgi-bin/browse-edgar?'+q
 text,transport,n=get(url)
 urls=list(dict.fromkeys(ARCHIVE_RE.findall(text)))
 accs=[]
 for u in urls:
  m=ACC_RE.search(u)
  if m and m.group(1) not in accs:accs.append(m.group(1))
 # also catch accessions rendered without archive absolute URL
 for a in ACC_RE.findall(text):
  if a not in accs:accs.append(a)
 return {'url':url,'transport':transport,'bytes':n,'accessions':accs[:30],'snippet':' '.join(text.split())[:1400]}

def main():
 rows=[]
 for i,x in enumerate(CIKS,1):
  try:r={**x,**browse(x['cik'])}
  except Exception as e:r={**x,'error':repr(e),'accessions':[]}
  rows.append(r);print(i,json.dumps(r),flush=True);time.sleep(.2)
 out={'purpose':'Fixed-CIK latest pre-2020 N-Q discovery for Gate B. CIKs were fixed from exact series continuity before Universe comparison.','rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({'ciks':len(rows),'withAccessions':sum(bool(r.get('accessions')) for r in rows),'counts':[len(r.get('accessions',[])) for r in rows]}),flush=True)
if __name__=='__main__':main()
