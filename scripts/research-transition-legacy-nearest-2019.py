#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,re,time,urllib.parse,urllib.request
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-legacy-nearest-2019.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
TARGETS={
 '0001329377':['S000010977','S000017177','S000017178'],
 '0001364608':['S000033237','S000050385'],
 '0001552740':['S000044209','S000053942','S000053943','S000053944','S000053945','S000053946','S000053947','S000053948'],
 '0001467831':['S000047480','S000050191'],
 '0001408970':['S000031813','S000055090','S000059263','S000067382'],
}
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
 return list(dict.fromkeys(ACC_RE.findall(text)))[:40]
def header(cik,acc):
 text,transport=get(f'{base(cik,acc)}/{acc}-index-headers.html')
 sids=list(dict.fromkeys(x.strip() for x in SID_RE.findall(text)))
 rm=REPORT_RE.search(text);fm=FORM_RE.search(text)
 docs=[]
 for typ,f in DOC_RE.findall(text):docs.append({'type':typ.upper(),'filename':f.strip(),'url':f'{base(cik,acc)}/{f.strip()}'})
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
 for cik,targets in TARGETS.items():
  accs=[]
  for form in FORMS:
   try:a=browse(cik,form);accs.extend(a);audits.append({'cik':cik,'form':form,'accessions':a})
   except Exception as e:audits.append({'cik':cik,'form':form,'error':repr(e)})
  for acc in list(dict.fromkeys(accs)):
   try:info=header(cik,acc);candidates.append(info);print('HEADER',cik,acc,info['form'],info['reportDate'],'series',len(info['seriesIds']),flush=True)
   except Exception as e:audits.append({'cik':cik,'accession':acc,'error':repr(e)})
   time.sleep(.05)
 chosen={}
 for cik,targets in TARGETS.items():
  for sid in targets:
   nf=first.get(sid);nrd=nf.get('reportDate') if nf else None
   opts=[c for c in candidates if c['cik']==cik and sid in c.get('seriesIds',[]) and c.get('reportDate') and (not nrd or c['reportDate']<nrd)]
   opts.sort(key=lambda x:(x['reportDate'],x['accession']),reverse=True)
   if opts:
    c=opts[0];gap=(date.fromisoformat(nrd)-date.fromisoformat(c['reportDate'])).days if nrd else None
    chosen[sid]={**c,'seriesId':sid,'nportReportDate':nrd,'daysToNport':gap}
    print('CHOSEN',sid,c['form'],c['reportDate'],'->',nrd,'gap',gap,c['accession'],flush=True)
 alltargets=set(sum(TARGETS.values(),[]));gaps=[x['daysToNport'] for x in chosen.values() if x.get('daysToNport') is not None]
 out={'purpose':'Choose the nearest pre-N-PORT legacy portfolio report for fixed transition series using only SEC series metadata and report dates. Forms searched: N-Q, N-CSR, N-CSRS. No holdings overlap or strategy returns used for selection.','targetSeries':len(alltargets),'resolvedSeries':len(chosen),'unresolvedSeries':sorted(alltargets-set(chosen)),'medianDaysToNport':sorted(gaps)[len(gaps)//2] if gaps else None,'chosen':chosen,'candidates':candidates,'audits':audits}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('chosen','candidates','audits')}),flush=True)
if __name__=='__main__':main()
