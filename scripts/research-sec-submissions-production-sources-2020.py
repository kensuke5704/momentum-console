#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.request,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-submissions-production-sources-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'application/json'}
TARGETS={
 'S000057700':('0001645194','ClearBridge Large Cap Growth ESG ETF','2019-11-29'),
 'S000063326':('0001479026','Goldman Sachs Motif Finance Reimagined ETF','2019-11-29'),
 'S000061208':('0001540305','PPTY - U.S. Diversified Real Estate ETF','2019-11-30'),
}
FORMS={'N-Q','N-CSR','N-CSRS','NPORT-EX','NPORT-P'}

def fetch_json(url):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

def rows_from_recent(d):
 r=d.get('filings',{}).get('recent',{});n=len(r.get('accessionNumber',[]));out=[]
 for i in range(n):
  out.append({k:(v[i] if i<len(v) else None) for k,v in r.items() if isinstance(v,list)})
 return out

def main():
 rows=[]
 for sid,(cik,name,boundary) in TARGETS.items():
  rec={'seriesId':sid,'seriesName':name,'cik':cik,'boundary':boundary}
  try:
   d=fetch_json(f'https://data.sec.gov/submissions/CIK{cik}.json')
   filings=rows_from_recent(d)
   # Include older shards listed by SEC if necessary.
   for f in d.get('filings',{}).get('files',[]):
    try:filings += rows_from_recent({'filings':{'recent':fetch_json('https://data.sec.gov/submissions/'+f['name'])}})
    except Exception as e:rec.setdefault('shardErrors',[]).append({'name':f.get('name'),'error':repr(e)})
   cand=[]
   for x in filings:
    form=(x.get('form') or '').upper();report=x.get('reportDate') or ''
    if form not in FORMS or not report or report>=boundary:continue
    if report<'2018-01-01':continue
    cand.append({'accession':x.get('accessionNumber'),'form':form,'filingDate':x.get('filingDate'),'reportDate':report,'primaryDocument':x.get('primaryDocument'),'primaryDocDescription':x.get('primaryDocDescription')})
   cand.sort(key=lambda x:(x['reportDate'],x.get('filingDate') or '',x.get('accession') or ''),reverse=True)
   rec['candidates']=cand[:30];rec['status']='OK'
  except Exception as e:rec['status']='ERROR';rec['error']=repr(e)
  rows.append(rec);print('SOURCE',json.dumps(rec),flush=True);time.sleep(.2)
 out={'purpose':'Official SEC submissions API inventory for potential complete-holdings filings preceding the first Production N-PORT report for the three exact 2020-01 Production source registrants. This is metadata-only; exact series continuity is validated in the filing document before use.','rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
