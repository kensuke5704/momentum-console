#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/jan2020-source-registrant-resolve.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
TARGETS=[
 {'seriesId':'S000057700','seriesName':'ClearBridge Large Cap Growth ESG ETF','accession':'0001752724-20-012434'},
 {'seriesId':'S000063326','seriesName':'Goldman Sachs Motif Finance Reimagined ETF','accession':'0001752724-20-013847'},
 {'seriesId':'S000061208','seriesName':'PPTY - U.S. Diversified Real Estate ETF','accession':'0001145549-20-003103'},
]
SID_RE=re.compile(r'<SERIES-ID>\s*([^<\r\n]+)',re.I)
NAME_RE=re.compile(r'(?:COMPANY CONFORMED NAME|Company Name)[:\s]+([^\r\n<]+)',re.I)

def get(url,timeout=20):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(3_000_000).decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.5)
 raise last or RuntimeError('fetch failed')

def main():
 rows=[]
 for t in TARGETS:
  seed=t['accession'].split('-')[0]
  url=f"https://www.sec.gov/Archives/edgar/data/{int(seed)}/{t['accession']}-index-headers.html"
  row={**t,'seedCik':seed,'headerUrl':url}
  try:
   text,transport=get(url);sids=list(dict.fromkeys(x.strip() for x in SID_RE.findall(text)));nm=NAME_RE.search(text)
   row.update({'transport':transport,'seriesIds':sids,'seriesConfirmed':t['seriesId'] in sids,'registrantName':nm.group(1).strip() if nm else None})
   if t['seriesId'] in sids: row['resolvedRegistrantCik']=seed
  except Exception as e: row['error']=repr(e)
  rows.append(row);print('ROW',json.dumps(row),flush=True)
 out={'purpose':'Use accession-prefix CIK only as a lookup seed. Accept it as registrant CIK only when the actual filing-time SEC header explicitly contains the target series ID. No holdings overlap or returns used.','resolved':sum(bool(r.get('resolvedRegistrantCik')) for r in rows),'targets':len(rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
