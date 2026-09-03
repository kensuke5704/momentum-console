#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('d',ROOT/'scripts'/'research-transition-legacy-nearest-2019.py')
d=importlib.util.module_from_spec(S);S.loader.exec_module(d)
OUT=ROOT/'data/research/production-jan2020-legacy-format-diagnostic.json'
TARGETS=[
 {'seriesId':'S000057700','seriesName':'ClearBridge Large Cap Growth ESG ETF','cik':'0001645194','accession':'0001193125-19-113628','form':'N-Q','reportDate':'2019-02-28'},
 {'seriesId':'S000061208','seriesName':'PPTY - U.S. Diversified Real Estate ETF','cik':'0001540305','accession':'0000898531-19-000551','form':'N-CSRS','reportDate':'2019-08-31'},
]
SCHED=re.compile(r'(?:PORTFOLIO|SCHEDULE) OF INVESTMENTS',re.I)
COMMON=re.compile(r'\bCOMMON STOCKS?\b|\bCOMMON SHARES?\b|\bREAL ESTATE INVESTMENT TRUSTS?\b',re.I)

def main():
 rows=[]
 for t in TARGETS:
  info=d.header(t['cik'],t['accession']);docs=info.get('documents',[])
  audit={**t,'documents':[]}
  for doc in docs:
   try:text,tr=d.get(doc['url'])
   except Exception as e:
    audit['documents'].append({**doc,'error':repr(e)});continue
   ls=text.splitlines();sched=[i for i,x in enumerate(ls) if SCHED.search(x)]
   title=[i for i,x in enumerate(ls) if t['seriesName'].lower() in x.lower()]
   windows=[]
   for m in sched[:80]:
    near_common=[k for k in range(m,min(len(ls),m+80)) if COMMON.search(ls[k])]
    prev_title=[i for i in title if i<=m and m-i<=300]
    if near_common or prev_title:
     windows.append({'scheduleLine':m+1,'scheduleText':ls[m].strip(),'nearestPrecedingTitleLine':prev_title[-1]+1 if prev_title else None,'titleDistance':m-prev_title[-1] if prev_title else None,'commonLines':[k+1 for k in near_common[:10]],'window':[{'line':j+1,'text':ls[j]} for j in range(max(0,m-12),min(len(ls),m+100)) if ls[j].strip()]})
   audit['documents'].append({**doc,'transport':tr,'lineCount':len(ls),'titleHits':[x+1 for x in title[:50]],'scheduleHits':[x+1 for x in sched[:80]],'windows':windows})
   print('DOC',json.dumps({'seriesId':t['seriesId'],'url':doc['url'],'lineCount':len(ls),'titles':len(title),'schedules':len(sched),'candidateWindows':len(windows)}),flush=True)
  rows.append(audit)
 out={'purpose':'Structural format diagnostic for the two preregistered nearest legacy sources used in the January 2020 hybrid transition shadow. No Production holdings, overlap, ranks, or returns are used for parsing decisions.','rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
