#!/usr/bin/env python3
from __future__ import annotations
import html,importlib.util,io,json,re,urllib.request,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INV=ROOT/'data/research/sec-marketwide-nq-inventory-h1-2006.json'
PREF=ROOT/'data/research/sec-etf-registrant-operational-prefilter-h1-2006.json'
OUT=ROOT/'data/research/sec-historical-etf-series-source-catalog-h1-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,application/zip,*/*','Accept-Encoding':'identity'}
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28'),('2006-03','2006-03-31'),('2006-04','2006-04-28'),('2006-05','2006-05-31'),('2006-06','2006-06-30')]
CORE={'485BPOS','485APOS','485BXT','N-1A','N-1A/A'};SUPP={'497'};FORMS=CORE|SUPP
SID_RE=re.compile(r'^S\d{9}$',re.I);EXPLICIT_ETF_CLASS=re.compile(r'\b(?:ETF\s+SHARES?|VIPER(?:\s+SHARES?)?|EXCHANGE[- ]TRADED)\b',re.I)
# Reuse the validated issuer-own operational grammar and the corrected filing-index structural parser.
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
rule=load_module('issuer_rule',ROOT/'scripts/research-sec-historical-etf-issuer-own-evidence-pilot-2006.py')
idxp=load_module('idxp',ROOT/'scripts/research-sec-marketwide-series-class-shard-q1-2006.py')
def fb(url,limit=4_000_000,timeout=20):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(limit),getattr(r,'status',None)
def ft(url,limit=1_500_000,timeout=18):
 errs=[]
 for u in (url,'https://r.jina.ai/'+url):
  try:b,s=fb(u,limit,timeout);return b.decode('latin-1','replace'),u,s,errs
  except Exception as e:errs.append({'transport':u,'error':type(e).__name__})
 raise RuntimeError(json.dumps(errs))
def master(y,q):
 base=f'https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}';zu=base+'/master.zip'
 try:
  b,_=fb(zu,25_000_000,45)
  with zipfile.ZipFile(io.BytesIO(b)) as z:n=next(x for x in z.namelist() if x.lower().endswith('master.idx'));return z.read(n).decode('latin-1','replace'),zu
 except Exception:
  t,u,_,_=ft(base+'/master.idx',25_000_000,50);return t,u
def load_prospectus(ciks):
 by=defaultdict(list);trs={}
 for y,qs in ((2005,range(1,5)),(2006,range(1,3))):
  for q in qs:
   t,tr=master(y,q);trs[f'{y}Q{q}']=tr
   for ln in t.splitlines():
    p=ln.split('|')
    if len(p)<5 or not p[0].strip().isdigit():continue
    cik,co,form,date,fn=[x.strip() for x in p[:5]];cik=cik.zfill(10);form=form.upper()
    if cik in ciks and form in FORMS and date<='2006-06-30':by[cik].append({'cik':cik,'company':co,'form':form,'dateFiled':date,'filename':fn})
 return by,trs
def ap(fn):
 m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',fn,re.I)
 if not m:return None
 return str(int(m.group(1))),m.group(2),m.group(2).replace('-','')
def iu(fn):
 p=ap(fn)
 return f'https://www.sec.gov/Archives/edgar/data/{p[0]}/{p[2]}/{p[1]}-index.html' if p else None
def su(fn):return 'https://www.sec.gov/Archives/'+fn.lstrip('/')
def parse_index_series(url):
 text,tr,status,prior=ft(url,1_500_000,16)
 records=idxp.parse_markdown_records(text) if tr.startswith('https://r.jina.ai/') else idxp.parse_html_records(text)
 series=[];current=None
 for r in records:
  if r.get('type')=='series' and SID_RE.fullmatch(r.get('seriesId','')):
   current={'seriesId':r['seriesId'].upper(),'seriesName':r.get('seriesName','').strip(),'classes':[]};series.append(current)
  elif r.get('type')=='class' and current is not None:current['classes'].append({'classId':r.get('classId'),'className':r.get('className',''),'ticker':r.get('ticker','')})
 ded=[];seen=set()
 for s in series:
  if s['seriesId'] in seen:continue
  seen.add(s['seriesId']);ded.append(s)
 return ded,tr,prior
def norm(s):return ' '.join(re.sub(r'[^A-Z0-9]+',' ',html.unescape(s or '').upper()).split())
def context(text,c,e,radius=30000):
 if not c or not e:return ''
 lo=max(0,min(c.start(),e.start())-radius);hi=min(len(text),max(c.end(),e.end())+radius);return text[lo:hi]
def select_monthly_prospectus(rows):
 chosen={}
 for month,asof in MONTHS:
  avail=[r for r in rows if r['dateFiled']<=asof]
  core=sorted((r for r in avail if r['form'] in CORE),key=lambda r:(r['dateFiled'],r['form'],r['filename']),reverse=True)
  supp=sorted((r for r in avail if r['form'] in SUPP),key=lambda r:(r['dateFiled'],r['form'],r['filename']),reverse=True)
  for r in ([core[0]] if core else [])+([supp[0]] if supp else []):chosen[r['filename']]=r
 return sorted(chosen.values(),key=lambda r:(r['dateFiled'],r['form'],r['filename']))
def main():
 inv=json.loads(INV.read_text());pref=json.loads(PREF.read_text());ciks=set(pref['positiveCiks']);pros,trs=load_prospectus(ciks)
 evidence=[];filing_diag=[]
 for cik in sorted(ciks):
  for f in select_monthly_prospectus(pros.get(cik,[])):
   rec={**f,'indexUrl':iu(f['filename']),'submissionUrl':su(f['filename'])}
   try:
    series,itr,iprior=parse_index_series(rec['indexUrl']);rec['indexTransport']=itr;rec['indexPriorErrors']=iprior;rec['indexSeriesCount']=len(series)
    text,strans,status,sprior=ft(rec['submissionUrl'],4_000_000,22);rec['submissionTransport']=strans;rec['submissionPriorErrors']=sprior
    c=rule.find(rule.CREATION,text);e=rule.find(rule.EXCHANGE,text);rec['creationIssuerOwnEvidence']=bool(c);rec['exchangeIssuerOwnEvidence']=bool(e)
    ctxnorm=norm(context(text,c,e));positive=[]
    if c and e:
     for s in series:
      explicit=any(EXPLICIT_ETF_CLASS.search(x.get('className') or '') for x in s['classes'])
      local=bool(s['seriesName'] and norm(s['seriesName']) and norm(s['seriesName']) in ctxnorm)
      bound=(len(series)==1) or local or explicit
      if bound:
       positive.append({'cik':cik,'seriesId':s['seriesId'],'seriesName':s['seriesName'],'evidenceDateFiled':f['dateFiled'],'evidenceForm':f['form'],'evidenceFilename':f['filename'],'binding':'SINGLE_SERIES_FILING' if len(series)==1 else ('LOCAL_SERIES_NAME' if local else 'EXPLICIT_ETF_CLASS')})
    rec['positiveSeriesCount']=len(positive);evidence.extend(positive)
   except Exception as ex:rec['error']=type(ex).__name__
   filing_diag.append(rec);print('PROSPECTUS',json.dumps({k:rec.get(k) for k in ('cik','form','dateFiled','indexSeriesCount','creationIssuerOwnEvidence','exchangeIssuerOwnEvidence','positiveSeriesCount','error')}),flush=True)
 # Earliest public operational evidence per Series ID.
 first={}
 for r in sorted(evidence,key=lambda x:(x['evidenceDateFiled'],x['seriesId'],x['evidenceFilename'])):
  if r['seriesId'] not in first:first[r['seriesId']]=r
 positive=list(first.values());posids=set(first)
 # Independently inspect all N-Q/N-Q-A filing-index metadata only for candidate registrants.
 nq=[];nq_diag=[]
 for row in [x for x in inv['rows'] if x['cik'] in ciks]:
  rec={k:row[k] for k in ('cik','company','form','dateFiled','filename','accession','indexUrl')}
  try:
   series,tr,prior=parse_index_series(row['indexUrl']);rec['transport']=tr;rec['priorErrors']=prior;rec['seriesCount']=len(series);rec['positiveSeriesIds']=[s['seriesId'] for s in series if s['seriesId'] in posids]
   for s in series:
    if s['seriesId'] in posids:nq.append({**row,'seriesId':s['seriesId'],'seriesName':s['seriesName'] or first[s['seriesId']]['seriesName']})
  except Exception as ex:rec['error']=type(ex).__name__;rec['seriesCount']=0;rec['positiveSeriesIds']=[]
  nq_diag.append(rec)
 # Deduplicate same series/accession and build monthly latest-public source snapshots.
 uniq={}
 for r in nq:uniq[(r['seriesId'],r['accession'])]=r
 nq=list(uniq.values())
 snaps=[]
 for month,asof in MONTHS:
  latest={}
  for r in nq:
   ev=first.get(r['seriesId'])
   if not ev or ev['evidenceDateFiled']>asof or r['dateFiled']>asof:continue
   cur=latest.get(r['seriesId'])
   if cur is None or (r['dateFiled'],r['accession'])>(cur['dateFiled'],cur['accession']):latest[r['seriesId']]=r
  src=sorted(latest.values(),key=lambda r:(r['seriesId'],r['dateFiled'],r['accession']))
  snaps.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(src),'sourceFilings':[{'seriesId':r['seriesId'],'seriesName':r['seriesName'],'accession':r['accession'],'cik':r['cik'],'registrant':r['company'],'filingDate':r['dateFiled'],'evidenceDateFiled':first[r['seriesId']]['evidenceDateFiled'],'evidenceForm':first[r['seriesId']]['evidenceForm']} for r in src]})
 out={'purpose':'Production-independent H1 2006 historical ETF source-series catalog. Candidate registrants come only from the market-wide operational prefilter. Final positive Series IDs require the validated issuer-own Creation Unit plus exchange-listing/trading conjunction in a deterministic month-end prospectus candidate, plus Series-ID filing binding by single-series filing, local series-name context, or explicit ETF/VIPER class. Monthly source snapshots then use only operational evidence and N-Q/N-Q-A filings public by that month end, taking the latest public filing per Series ID. No known source accession list, holdings outcomes, ranks, returns, or strategy results are used for selection.','inventoryArtifactId':9946255797,'prefilterSourceRunId':33897558123,'candidateRegistrantCount':len(ciks),'positiveSeriesCount':len(positive),'positiveSeries':sorted(positive,key=lambda r:r['seriesId']),'prospectusEvidenceRecords':len(evidence),'nqPositiveSeriesFilingCount':len(nq),'monthSnapshots':snaps,'masterTransports':trs,'prospectusDiagnostics':filing_diag,'nqDiagnostics':nq_diag}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('positiveSeries','monthSnapshots','masterTransports','prospectusDiagnostics','nqDiagnostics')}),flush=True)
 for s in snaps:print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)
if __name__=='__main__':main()
