#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.parse,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/'data/universe-history.json'
OUT=ROOT/'data/research/gate-b-production-source-legacy-discovery-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
CIK_RE=re.compile(r'CENTRAL INDEX KEY:\s*(\d+)',re.I)
SERIES_RE=re.compile(r'<SERIES-ID>\s*([^<\r\n]+)',re.I)
ACC_RE=re.compile(r'\b(\d{10}-\d{2}-\d{6})\b')
REPORT_RE=re.compile(r'(?:CONFORMED PERIOD OF REPORT|PERIOD OF REPORT):\s*(\d{8})',re.I)
FORM_RE=re.compile(r'CONFORMED SUBMISSION TYPE:\s*(N-Q|N-CSR|N-CSRS)\b',re.I)
ARCHIVE_RE=re.compile(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"\'<>\)]+',re.I)

def get(url,timeout=30):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(4_000_000).decode('utf-8','replace'),u
  except Exception as e:last=repr(e);time.sleep(.4)
 raise RuntimeError(last or 'fetch failed')

def months(raw):
 if isinstance(raw,list):return raw
 if isinstance(raw,dict):
  for k in ('months','history'):
   if isinstance(raw.get(k),list):return raw[k]
  return [v for v in raw.values() if isinstance(v,dict) and v.get('signalMonth')]
 return []

def submission_url(acc):
 prefix=str(int(re.sub(r'\D','',acc)[:10]));nodash=acc.replace('-','')
 return f'https://www.sec.gov/Archives/edgar/data/{prefix}/{nodash}/{acc}.txt'

def browse(cik,form,dateb='20200101'):
 q=urllib.parse.urlencode({'action':'getcompany','CIK':cik,'type':form,'dateb':dateb,'owner':'exclude','count':'100'})
 text,tr=get('https://www.sec.gov/cgi-bin/browse-edgar?'+q)
 accs=[]
 for a in ACC_RE.findall(text):
  if a not in accs:accs.append(a)
 return accs,tr

def header_for(acc):
 text,tr=get(submission_url(acc));
 ciks=[]
 for x in CIK_RE.findall(text):
  z=x.zfill(10)
  if z not in ciks:ciks.append(z)
 sids=[]
 for x in SERIES_RE.findall(text):
  x=x.strip()
  if x not in sids:sids.append(x)
 m=REPORT_RE.search(text);fm=FORM_RE.search(text)
 return {'accession':acc,'transport':tr,'ciks':ciks,'seriesIds':sids,'reportDate':(m.group(1)[:4]+'-'+m.group(1)[4:6]+'-'+m.group(1)[6:]) if m else None,'form':fm.group(1).upper() if fm else None}

def main():
 hist=json.loads(HIST.read_text());m=next(x for x in months(hist) if x.get('signalMonth')=='2020-01')
 rows=[]
 for src in m.get('sourceFilings',[]):
  sid=src.get('seriesId');acc=src.get('accession')
  row={'seriesId':sid,'seriesName':src.get('seriesName'),'nportAccession':acc,'nportFilingDate':src.get('filingDate')}
  try:
   nh=header_for(acc);row['nportHeader']=nh
   # Accept a candidate registrant CIK only when the current N-PORT submission itself contains the target series ID.
   if sid not in nh.get('seriesIds',[]):
    row['status']='TARGET_SERIES_NOT_IN_NPORT_SUBMISSION';rows.append(row);print('SOURCE',json.dumps(row),flush=True);continue
   legacy=[]
   for cik in nh.get('ciks',[]):
    for form in ('N-Q','N-CSR','N-CSRS'):
     try:
      accs,tr=browse(cik,form,'20200101')
     except Exception as e:
      row.setdefault('browseErrors',[]).append({'cik':cik,'form':form,'error':repr(e)});continue
     for la in accs[:30]:
      try:
       h=header_for(la)
      except Exception:continue
      if sid not in h.get('seriesIds',[]):continue
      if h.get('reportDate') and h['reportDate']<'2019-11-29':
       legacy.append({**h,'registrantCik':cik})
   # Selection strictly latest reportDate before first N-PORT report boundary, accession tie-break; no holdings used.
   legacy.sort(key=lambda x:(x.get('reportDate') or '',x.get('accession') or ''),reverse=True)
   row['legacyCandidates']=legacy[:10];row['chosenLegacy']=legacy[0] if legacy else None;row['status']='RESOLVED' if legacy else 'UNRESOLVED'
  except Exception as e:row['status']='ERROR';row['error']=repr(e)
  rows.append(row);print('SOURCE',json.dumps(row),flush=True);time.sleep(.2)
 out={'purpose':'Metadata-only discovery of the nearest pre-NPORT legacy filing for the exact series that actually generated Production 2020-01 Universe. Candidate selection uses target seriesId continuity and report dates only; no holdings overlap, ranks, or returns.', 'signalMonth':'2020-01','sourceCount':len(rows),'resolvedCount':sum(r.get('status')=='RESOLVED' for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
