#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,re,time,urllib.parse,urllib.request
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-legacy-nearest-expanded-2019.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
# Registrants fixed from same-series continuity evidence before overlap inspection.
CIKS=['0001329377','0001364608','0001552740','0001467831','0001408970']
FORMS=['N-Q','N-CSR','N-CSRS']
ACC_RE=re.compile(r'(\d{10}-\d{2}-\d{6})')
SID_RE=re.compile(r'<SERIES-ID>\s*([^<\r\n]+)',re.I)
REPORT_RE=re.compile(r'(?:Period of Report|CONFORMED PERIOD OF REPORT[:\s]+)\s*(\d{4}[-/]?\d{2}[-/]?\d{2}|\d{8})',re.I)
FORM_RE=re.compile(r'(?:Type|CONFORMED SUBMISSION TYPE[:\s]+)\s*([A-Z0-9-]+)',re.I)
DOC_RE=re.compile(r'<TYPE>(N-Q|N-CSR|N-CSRS)\b.*?<FILENAME>\s*([^<\r\n]+)',re.I|re.S)
def get(url,timeout=30):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:raw=r.read(3_000_000)
   return raw.decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.5)
 raise last or RuntimeError('fetch failed')
def normdate(x):
 d=re.sub(r'\D','',x or '')
 return f'{d[:4]}-{d[4:6]}-{d[6:8]}' if len(d)>=8 else None
def base(cik,acc):return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}'
def browse(cik,form):
 q=urllib.parse.urlencode({'action':'getcompany','CIK':cik,'type':form,'dateb':'20191231','owner':'exclude','count':'100'})
 text,_=get('https://www.sec.gov/cgi-bin/browse-edgar?'+q)
 return list(dict.fromkeys(ACC_RE.findall(text)))[:50]
def header(cik,acc):
 text,transport=get(f'{base(cik,acc)}/{acc}-index-headers.html')
 sids=list(dict.fromkeys(x.strip() for x in SID_RE.findall(text)))
 rm=REPORT_RE.search(text);fm=FORM_RE.search(text)
 docs=[{'type':typ.upper(),'filename':f.strip(),'url':f'{base(cik,acc)}/{f.strip()}'} for typ,f in DOC_RE.findall(text)]
 return {'cik':cik,'accession':acc,'reportDate':normdate(rm.group(1)) if rm else None,'form':fm.group(1).upper() if fm else None,'seriesIds':sids,'documents':docs,'transport':transport}
def earliest_nport(filings):
 d={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in d:d[sid]=f
 return d
def main():
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:boot=json.load(fh)
 filings=boot.get('snapshots',boot) if isinstance(boot,dict) else boot;first=earliest_nport(filings)
 candidates=[];audits=[]
 for cik in CIKS:
  accs=[]
  for form in FORMS:
   try:
    a=browse(cik,form);accs.extend(a);audits.append({'cik':cik,'form':form,'accessions':a})
   except Exception as e:audits.append({'cik':cik,'form':form,'error':repr(e)})
  for acc in list(dict.fromkeys(accs)):
   try:
    info=header(cik,acc);candidates.append(info);print('HEADER',cik,acc,info['form'],info['reportDate'],'series',len(info['seriesIds']),flush=True)
   except Exception as e:audits.append({'cik':cik,'accession':acc,'error':repr(e)})
   time.sleep(.03)
 # Candidate population is defined only by exact legacy header series IDs intersected with early N-PORT IDs.
 legacy_to_cik={}
 for c in candidates:
  for sid in c.get('seriesIds',[]):
   if sid in first: legacy_to_cik.setdefault(sid,set()).add(c['cik'])
 unique={sid:next(iter(ciks)) for sid,ciks in legacy_to_cik.items() if len(ciks)==1}
 chosen={}
 for sid,cik in unique.items():
  nf=first[sid];nrd=nf.get('reportDate')
  opts=[c for c in candidates if c['cik']==cik and sid in c.get('seriesIds',[]) and c.get('reportDate') and nrd and c['reportDate']<nrd]
  opts.sort(key=lambda x:(x['reportDate'],x['accession']),reverse=True)
  if not opts:continue
  c=opts[0];gap=(date.fromisoformat(nrd)-date.fromisoformat(c['reportDate'])).days
  chosen[sid]={**c,'seriesId':sid,'seriesName':nf.get('seriesName') or nf.get('fundName'),'nportReportDate':nrd,'daysToNport':gap}
  print('CHOSEN',sid,c['form'],c['reportDate'],'->',nrd,'gap',gap,flush=True)
 gaps=[x['daysToNport'] for x in chosen.values()]
 short={sid:x for sid,x in chosen.items() if x['daysToNport']<=184}
 out={'purpose':'Expand transition Gate B precursor population using exact SEC legacy header series IDs intersected with early N-PORT series IDs for preregistered registrants. No holdings overlap or strategy returns used.','registrants':CIKS,'intersectedSeries':len(unique),'resolvedSeries':len(chosen),'shortGapSeriesLe184Days':len(short),'medianDaysToNport':sorted(gaps)[len(gaps)//2] if gaps else None,'shortGapSeries':short,'chosen':chosen,'ambiguousRegistrantSeries':{sid:sorted(v) for sid,v in legacy_to_cik.items() if len(v)>1},'audits':audits}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('chosen','shortGapSeries','audits','ambiguousRegistrantSeries')}),flush=True)
if __name__=='__main__':main()
