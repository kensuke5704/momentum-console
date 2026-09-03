#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/jan2020-accession-master-index-resolve.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
TARGETS={
 '0001752724-20-012434':{'seriesId':'S000057700','seriesName':'ClearBridge Large Cap Growth ESG ETF'},
 '0001752724-20-013847':{'seriesId':'S000063326','seriesName':'Goldman Sachs Motif Finance Reimagined ETF'},
 '0001145549-20-003103':{'seriesId':'S000061208','seriesName':'PPTY - U.S. Diversified Real Estate ETF'},
}

def get(url,timeout=30):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(8_000_000).decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.5)
 raise last or RuntimeError('fetch failed')

def main():
 url='https://www.sec.gov/Archives/edgar/full-index/2020/QTR1/master.idx'
 text,transport=get(url)
 rows=[]
 for acc,meta in TARGETS.items():
  hits=[]
  needle=acc.replace('-','')
  for line in text.splitlines():
   if acc in line or needle in line:
    parts=line.split('|')
    if len(parts)>=5:
     cik,name,form,filing_date,filename=parts[:5]
     hits.append({'cik':cik.zfill(10),'registrantName':name,'form':form,'filingDate':filing_date,'filename':filename})
  row={**meta,'accession':acc,'hits':hits,'uniqueHit':len(hits)==1}
  if len(hits)==1: row.update({'resolvedRegistrantCik':hits[0]['cik'],'resolvedRegistrantName':hits[0]['registrantName'],'form':hits[0]['form'],'filingDate':hits[0]['filingDate'],'filename':hits[0]['filename']})
  rows.append(row);print('ROW',json.dumps(row),flush=True)
 out={'purpose':'Exact accession-to-registrant resolution from the official SEC 2020 Q1 master index. No accession-prefix assumption, holdings overlap, or returns used.','transport':transport,'resolved':sum(bool(r.get('resolvedRegistrantCik')) for r in rows),'targets':len(rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
