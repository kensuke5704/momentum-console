#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,re,time,urllib.request
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/jan2020-source-legacy-fast.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'application/json,text/plain,text/html,*/*'}
TARGETS={'0001645194':['S000057700'],'0001479026':['S000063326'],'0001540305':['S000061208']}
FORMS={'N-Q','N-CSR','N-CSRS'}
SID_RE=re.compile(r'<SERIES-ID>\s*([^<\r\n]+)',re.I)
REPORT_RE=re.compile(r'(?:Period of Report|CONFORMED PERIOD OF REPORT[:\s]+)\s*(\d{4}[-/]?\d{2}[-/]?\d{2}|\d{8})',re.I)
FORM_RE=re.compile(r'(?:Type|CONFORMED SUBMISSION TYPE[:\s]+)\s*([A-Z0-9-]+)',re.I)
DOC_RE=re.compile(r'<TYPE>(N-Q|N-CSR|N-CSRS)\b.*?<FILENAME>\s*([^<\r\n]+)',re.I|re.S)

def get(url,timeout=25):
 last=None
 for u in (url,'https://r.jina.ai/'+url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(5_000_000).decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.3)
 raise last or RuntimeError('fetch failed')

def normdate(x):
 d=re.sub(r'\D','',x or '')
 return f'{d[:4]}-{d[4:6]}-{d[6:8]}' if len(d)>=8 else None

def base(cik,acc):return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}'

def header(cik,acc):
 text,transport=get(f'{base(cik,acc)}/{acc}-index-headers.html')
 sids=list(dict.fromkeys(x.strip() for x in SID_RE.findall(text)))
 rm=REPORT_RE.search(text);fm=FORM_RE.search(text)
 docs=[{'type':typ.upper(),'filename':fn.strip(),'url':f'{base(cik,acc)}/{fn.strip()}'} for typ,fn in DOC_RE.findall(text)]
 return {'cik':cik,'accession':acc,'reportDate':normdate(rm.group(1)) if rm else None,'form':fm.group(1).upper() if fm else None,'seriesIds':sids,'documents':docs,'transport':transport}

def recent_rows(cik):
 text,transport=get(f'https://data.sec.gov/submissions/CIK{cik}.json')
 d=json.loads(text);r=d.get('filings',{}).get('recent',{})
 keys=['accessionNumber','filingDate','reportDate','form','primaryDocument']
 n=len(r.get('accessionNumber',[]));rows=[]
 for i in range(n):
  row={k:(r.get(k,[None]*n)[i] if i<len(r.get(k,[])) else None) for k in keys}
  if row.get('form') in FORMS and (row.get('filingDate') or '')<='2019-12-31':rows.append(row)
 return rows,transport,d.get('filings',{}).get('files',[])

def earliest_nport(fs):
 out={}
 for f in sorted(fs,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in out:out[sid]=f
 return out

def main():
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 fs=b.get('snapshots',b) if isinstance(b,dict) else b;first=earliest_nport(fs)
 candidates=[];aud=[]
 for cik,targets in TARGETS.items():
  try:
   rows,tr,older=recent_rows(cik);aud.append({'cik':cik,'recentTransport':tr,'candidateRows':len(rows),'olderFiles':older})
  except Exception as e:
   aud.append({'cik':cik,'error':repr(e)});continue
  for r in rows:
   try:
    h=header(cik,r['accessionNumber']);candidates.append(h);print('HEADER',cik,r['accessionNumber'],h['form'],h['reportDate'],h['seriesIds'],flush=True)
   except Exception as e:aud.append({'cik':cik,'accession':r['accessionNumber'],'error':repr(e)})
 chosen={}
 for cik,targets in TARGETS.items():
  for sid in targets:
   nf=first.get(sid);nrd=nf.get('reportDate') if nf else None
   opts=[c for c in candidates if c['cik']==cik and sid in c.get('seriesIds',[]) and c.get('reportDate') and (not nrd or c['reportDate']<nrd)]
   opts.sort(key=lambda x:(x['reportDate'],x['accession']),reverse=True)
   if opts:
    c=opts[0];gap=(date.fromisoformat(nrd)-date.fromisoformat(c['reportDate'])).days if nrd else None
    chosen[sid]={**c,'seriesId':sid,'nportReportDate':nrd,'daysToNport':gap};print('CHOSEN',json.dumps(chosen[sid]),flush=True)
 alltargets=set(sum(TARGETS.values(),[]))
 out={'purpose':'Fast metadata-only legacy discovery for exact Jan 2020 Production source series using SEC submissions accession lists, followed by filing-time series-ID confirmation. No holdings overlap or returns used.','targetSeries':len(alltargets),'resolvedSeries':len(chosen),'unresolvedSeries':sorted(alltargets-set(chosen)),'chosen':chosen,'candidates':candidates,'audits':aud}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('chosen','candidates','audits')}),flush=True)
if __name__=='__main__':main()
