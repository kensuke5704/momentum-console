#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-daily-index-nq-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
DATES=[('2006','QTR1','20060228'),('2006','QTR2','20060531')]
CHUNK=65536
ROW_RE=re.compile(r'^(.*?)\s{2,}(N-Q(?:/A)?)\s+(\d{10})\s+(\d{4}-\d{2}-\d{2})\s+(edgar/data/\S+)$')

def fetch_range(url,start,end):
 h=dict(UA);h['Range']=f'bytes={start}-{end}'
 req=urllib.request.Request(url,headers=h)
 with urllib.request.urlopen(req,timeout=18) as r:return r.read().decode('latin1','replace'),r.status,r.headers.get('Content-Range')
def parse_form_chunk(text):
 rows=[]
 for line in text.splitlines():
  if 'N-Q' not in line:continue
  # Form index fixed-width grammar: company | form | CIK | date | path separated by >=2 spaces.
  parts=re.split(r'\s{2,}',line.strip())
  if len(parts)>=5:
   company,form,cik,date,path=parts[0],parts[1],parts[2],parts[3],parts[4]
   if form.upper() in {'N-Q','N-Q/A'} and cik.isdigit() and path.startswith('edgar/data/'):
    rows.append({'cik':cik,'company':company,'form':form,'date':date,'path':path})
 return rows
def main():
 results=[]
 for y,q,d in DATES:
  url=f'https://www.sec.gov/Archives/edgar/daily-index/{y}/{q}/form.{d}.idx';rows=[];attempts=[];seen=set();found=False
  for n in range(0,40):
   start=n*CHUNK;end=start+CHUNK-1
   try:text,status,cr=fetch_range(url,start,end)
   except Exception as e:
    attempts.append({'range':[start,end],'error':type(e).__name__});continue
   attempts.append({'range':[start,end],'status':status,'contentRange':cr,'bytes':len(text.encode("latin1","replace")),'containsNQ':'N-Q' in text})
   for r in parse_form_chunk(text):
    k=(r['cik'],r['form'],r['date'],r['path'])
    if k not in seen:seen.add(k);rows.append(r)
   if 'N-Q' in text:found=True
   # form index is sorted by form type. Once we saw N-Q and the next chunk has moved beyond N-Q, stop.
   if found and 'N-Q' not in text:break
   # 416/empty after EOF.
   if not text:break
  r={'date':d,'url':url,'rangeChunkBytes':CHUNK,'rangeAttemptCount':len(attempts),'nqCount':len(rows),'uniqueCiks':len({x['cik'] for x in rows}),'attempts':attempts,'rows':rows};results.append(r);print('DAY',json.dumps({k:v for k,v in r.items() if k not in ('rows','attempts')}),flush=True)
  for x in rows[:30]:print('NQ',json.dumps(x),flush=True)
 out={'purpose':'Transport/source-discovery pilot using HTTP Range over SEC daily form indexes instead of blocked full-file/quarterly downloads. Form index is sorted by form type; chunks are scanned until the N-Q block is passed. Only N-Q/N-Q-A filing metadata is extracted; no holdings, ranks or returns used.','days':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
