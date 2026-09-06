#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import html
import importlib.util
import json
import re
import threading
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT=ROOT/'data/research/country-primary-cover-recovery-v29.json'

def load(path):
 spec=importlib.util.spec_from_file_location('country_cover_base',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load(ROOT/'scripts/research-country-index-headers-recovery-v29.py')

# Only explicit US jurisdiction names are promoted. Foreign/ambiguous values remain UNKNOWN.
US_JURISDICTIONS={
 'ALABAMA','ALASKA','ARIZONA','ARKANSAS','CALIFORNIA','COLORADO','CONNECTICUT','DELAWARE','FLORIDA','GEORGIA','HAWAII','IDAHO','ILLINOIS','INDIANA','IOWA','KANSAS','KENTUCKY','LOUISIANA','MAINE','MARYLAND','MASSACHUSETTS','MICHIGAN','MINNESOTA','MISSISSIPPI','MISSOURI','MONTANA','NEBRASKA','NEVADA','NEW HAMPSHIRE','NEW JERSEY','NEW MEXICO','NEW YORK','NORTH CAROLINA','NORTH DAKOTA','OHIO','OKLAHOMA','OREGON','PENNSYLVANIA','RHODE ISLAND','SOUTH CAROLINA','SOUTH DAKOTA','TENNESSEE','TEXAS','UTAH','VERMONT','VIRGINIA','WASHINGTON','WEST VIRGINIA','WISCONSIN','WYOMING','DISTRICT OF COLUMBIA'
}
FORM_PRIORITY={'10-K':0,'10-K/A':1,'10-Q':2,'10-Q/A':3,'8-K':4,'8-K/A':5,'DEF 14A':6,'DEFA14A':7,'PRE 14A':8,'11-K':9,'S-8':10,'S-8 POS':11}
CACHE={};LOCK=threading.Lock()
LABEL_RE=re.compile(r'(?:State\s+or\s+other\s+jurisdiction\s+of\s+(?:incorporation|organization)|State\s+of\s+incorporation)',re.I)

def seed(row):
 vals={str(a.get('seedCik')).zfill(10) for a in row.get('attempts',[]) if a.get('seedSource')=='HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME' and a.get('historicalExactCikCount')==1 and a.get('seedCik')}
 return next(iter(vals)) if len(vals)==1 else None

def issuer_forms(row):
 out=[]
 for x in row.get('issuerVariants',[]):
  for f in base.cleaned_forms(str(x)):
   n=base.normalize_company(f)
   if n and n not in out:out.append(n)
 return out

def fetch_submission(filename):
 with LOCK:
  if filename in CACHE:return CACHE[filename]
 url='https://www.sec.gov/Archives/'+filename.lstrip('/')
 proxy='https://r.jina.ai/'+url
 req=urllib.request.Request(proxy,headers=base.UA)
 with urllib.request.urlopen(req,timeout=12) as r:text=r.read(1_500_000).decode('latin-1','replace')
 result=(text,proxy)
 with LOCK:CACHE[filename]=result
 return result

def explicit_us_jurisdiction(text,issuer_norms):
 clean=html.unescape(re.sub(r'<[^>]*>',' ',text)).replace('\r',' ')
 clean=re.sub(r'\s+',' ',clean)
 # Require historical issuer name to occur in the filing text; the CIK is already fixed by master index.
 nhead=base.normalize_company(clean[:120000])
 if not any(x in nhead for x in issuer_norms):return None
 found=set()
 for m in LABEL_RE.finditer(clean):
  window=clean[max(0,m.start()-300):m.end()+650].upper()
  for j in US_JURISDICTIONS:
   if re.search(r'(?<![A-Z])'+re.escape(j)+r'(?![A-Z])',window):found.add(j)
 # A unique explicit US jurisdiction is required; conflicts remain UNKNOWN.
 return next(iter(found)) if len(found)==1 else None

def resolve_one(row,cik,by_cik):
 report=row.get('asOfReportDate'); norms=issuer_forms(row)
 rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':report,'issuerVariants':row.get('issuerVariants',[]),'historicalExactCik':cik,'classification':'UNKNOWN','attempts':[]}
 candidates=[x for x in by_cik.get(cik,[]) if report and x['dateFiled']<=report and x['form'] in FORM_PRIORITY]
 candidates=sorted(candidates,key=lambda x:(FORM_PRIORITY[x['form']],-int(x['dateFiled'].replace('-','')),x['filename']))[:3]
 for fr in candidates:
  try:text,tr=fetch_submission(fr['filename'])
  except Exception as e:rec['attempts'].append({'form':fr['form'],'dateFiled':fr['dateFiled'],'filename':fr['filename'],'error':type(e).__name__});continue
  jurisdiction=explicit_us_jurisdiction(text,norms)
  rec['attempts'].append({'form':fr['form'],'dateFiled':fr['dateFiled'],'filename':fr['filename'],'transport':tr,'explicitUsJurisdiction':jurisdiction})
  if jurisdiction:
   rec.update({'classification':'US','resolutionSource':'PIT_PRIMARY_DOCUMENT_EXPLICIT_US_JURISDICTION','stateOrJurisdiction':jurisdiction,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'evidenceFilename':fr['filename'],'evidenceTransport':tr});return rec
 return rec

def main():
 data=json.loads(SRC.read_text());unknown=[r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN']
 seeded=[(r,seed(r)) for r in unknown];seeded=[x for x in seeded if x[1]]
 years=sorted({int(r['asOfReportDate'][:4]) for r,_ in seeded if r.get('asOfReportDate')});master,transports=base.load_master(years);by=defaultdict(list)
 for r in master:by[str(r['cik']).zfill(10)].append(r)
 results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
  futs=[ex.submit(resolve_one,r,cik,by) for r,cik in seeded]
  for i,f in enumerate(concurrent.futures.as_completed(futs),1):
   results.append(f.result())
   if i%200==0:print('PROGRESS',json.dumps({'done':i,'resolvedUS':sum(x['classification']=='US' for x in results),'cache':len(CACHE)}),flush=True)
 results.sort(key=lambda r:((r.get('ticker') or ''),(r.get('securityId') or ''),(r.get('asOfReportDate') or '')))
 out={'purpose':'Uniform return-independent PIT recovery of strict-country UNKNOWN identities using explicit US state/jurisdiction text in pre-report-date SEC issuer filings. Identity remains frozen to historical exact issuer-form -> unique CIK. A row is promoted to US only if the historical issuer name appears in the filing and exactly one full US jurisdiction name occurs in a bounded window around an incorporation/organization jurisdiction label. Non-US or ambiguous cover values remain UNKNOWN. No current metadata, fuzzy matching, US default, ranks, returns or strategy outcomes.','inputUnknownCount':len(unknown),'seededQueryCount':len(seeded),'seededCikCount':len({c for _,c in seeded}),'resolvedUSCount':sum(r['classification']=='US' for r in results),'remainingSeededUnknownCount':sum(r['classification']=='UNKNOWN' for r in results),'masterYears':years,'masterIndexTransports':transports,'submissionCacheCount':len(CACHE),'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)
if __name__=='__main__':main()
