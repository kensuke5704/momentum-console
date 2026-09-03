#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.parse,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/'data/universe-history.json'
OUT=ROOT/'data/research/gate-b-production-source-legacy-discovery-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
ACC_RE=re.compile(r'\b(\d{10}-\d{2}-\d{6})\b')
SERIES_TEXT_RE=re.compile(r'\bSeries\s+(S\d{9})\b',re.I)
REPORT_TEXT_RE=re.compile(r'Period of Report\s*(\d{4}-\d{2}-\d{2}|\d{8})',re.I)
FORM_TEXT_RE=re.compile(r'Form\s+(N-Q|N-CSR|N-CSRS)\b',re.I)

REGISTRANT_CIK={
 'S000057700':'0001645194',
 'S000063326':'0001479026',
 'S000061208':'0001540305',
}
FIRST_NPORT_REPORT={'S000057700':'2019-11-29','S000063326':'2019-11-29','S000061208':'2019-11-30'}

def get(url,timeout=25):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(4_000_000).decode('utf-8','replace'),u
  except Exception as e:last=repr(e);time.sleep(.25)
 raise RuntimeError(last or 'fetch failed')

def months(raw):
 if isinstance(raw,list):return raw
 if isinstance(raw,dict):
  for k in ('months','history'):
   if isinstance(raw.get(k),list):return raw[k]
  return [v for v in raw.values() if isinstance(v,dict) and v.get('signalMonth')]
 return []

def base(cik,acc):return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}'

def browse(cik,form,dateb='20200131'):
 q=urllib.parse.urlencode({'action':'getcompany','CIK':cik,'type':form,'dateb':dateb,'owner':'exclude','count':'40'})
 text,tr=get('https://www.sec.gov/cgi-bin/browse-edgar?'+q)
 accs=[]
 for a in ACC_RE.findall(text):
  if a not in accs:accs.append(a)
 return accs,tr

def filing_index(cik,acc,form):
 url=f'{base(cik,acc)}/{acc}-index-headers.html';text,tr=get(url)
 sids=list(dict.fromkeys(x.upper() for x in SERIES_TEXT_RE.findall(text)))
 m=REPORT_TEXT_RE.search(text);rd=m.group(1) if m else None
 if rd and '-' not in rd:rd=rd[:4]+'-'+rd[4:6]+'-'+rd[6:]
 fm=FORM_TEXT_RE.search(text)
 return {'accession':acc,'registrantCik':cik,'transport':tr,'seriesIds':sids,'reportDate':rd,'form':fm.group(1).upper() if fm else form,'indexUrl':url}

def main():
 hist=json.loads(HIST.read_text());m=next(x for x in months(hist) if x.get('signalMonth')=='2020-01')
 rows=[]
 for src in m.get('sourceFilings',[]):
  sid=src.get('seriesId');cik=REGISTRANT_CIK.get(sid);boundary=FIRST_NPORT_REPORT.get(sid)
  row={'seriesId':sid,'seriesName':src.get('seriesName'),'nportAccession':src.get('accession'),'nportFilingDate':src.get('filingDate'),'registrantCik':cik,'firstNportReportDate':boundary}
  if not cik or not boundary:
   row['status']='NO_VERIFIED_REGISTRANT';rows.append(row);print('SOURCE',json.dumps(row),flush=True);continue
  legacy=[]
  for form in ('N-Q','N-CSR','N-CSRS'):
   try:accs,tr=browse(cik,form,'20200131')
   except Exception as e:
    row.setdefault('browseErrors',[]).append({'form':form,'error':repr(e)});continue
   for acc in accs[:12]:
    try:h=filing_index(cik,acc,form)
    except Exception:continue
    if sid not in h.get('seriesIds',[]):continue
    if h.get('reportDate') and h['reportDate']<boundary:legacy.append(h)
  legacy.sort(key=lambda x:(x.get('reportDate') or '',x.get('accession') or ''),reverse=True)
  row['legacyCandidates']=legacy[:10];row['chosenLegacy']=legacy[0] if legacy else None;row['status']='RESOLVED' if legacy else 'UNRESOLVED'
  rows.append(row);print('SOURCE',json.dumps(row),flush=True);time.sleep(.1)
 out={'purpose':'Metadata-only discovery of nearest pre-NPORT legacy filing for the exact series that actually generated Production 2020-01 Universe. Registrant CIKs are exact SEC series/class identifiers; candidate filing selection uses exact seriesId continuity and report dates only. No holdings overlap, ranks, or returns used.','signalMonth':'2020-01','sourceCount':len(rows),'resolvedCount':sum(r.get('status')=='RESOLVED' for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
