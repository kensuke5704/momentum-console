#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT=ROOT/'data/research/country-index-headers-recovery-v29.json'

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('base',ROOT/'scripts/research-sec-index-headers-country-pilot-2006.py')

def exact_candidates(row,master_rows):
 report=row.get('asOfReportDate'); forms=[]
 for issuer in row.get('issuerVariants',[]):
  for f in base.old.cleaned_forms(str(issuer)) if hasattr(base.old,'cleaned_forms') else [issuer]:
   if f and f not in forms: forms.append(f)
 # use the same normalization as the accepted historical resolver; require exactly one CIK across all exact forms
 by=defaultdict(list); matched_forms=[]
 for form in forms:
  target=base.normalize_company(form)
  exact=[r for r in master_rows if r.get('form') in base.ISSUER_FORMS and report and r.get('dateFiled')<=report and r.get('normalizedCompany')==target]
  if exact: matched_forms.append(form)
  for r in exact: by[str(r.get('cik') or '').zfill(10)].append(r)
 if len(by)!=1: return None,[],matched_forms
 cik=next(iter(by)); rows=sorted(by[cik],key=base.filing_sort_key)
 # de-dupe same accession
 seen=set();out=[]
 for r in rows:
  fn=r.get('filename')
  if fn and fn not in seen: seen.add(fn);out.append(r)
 return cik,out,matched_forms

def main():
 data=json.loads(SRC.read_text())
 unknown=[r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN']
 years=sorted({int(r['asOfReportDate'][:4]) for r in unknown if r.get('asOfReportDate')})
 master,transports=base.load_master(years)
 results=[];resolved=0;us=0;nonus=0;errors=0
 for i,row in enumerate(unknown):
  cik,candidates,forms=exact_candidates(row,master)
  rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'issuerVariants':row.get('issuerVariants',[]),'historicalExactCik':cik,'matchedIssuerForms':forms,'classification':'UNKNOWN','attempts':[]}
  if cik:
   for fr in candidates[:6]:
    for issuer in forms:
     try:
      text,tr=base.header_page(fr['filename']);st,name=base.flat_header_entity_state(issuer,cik,text)
      rec['attempts'].append({'form':fr.get('form'),'dateFiled':fr.get('dateFiled'),'filename':fr.get('filename'),'transport':tr,'stateCode':st,'historicalEntityName':name})
      if st:
       rec.update({'classification':'US' if st in base.old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_INDEX_HEADERS_COMPANY_DATA_STATE','historicalEntityName':name,'evidenceForm':fr.get('form'),'evidenceDateFiled':fr.get('dateFiled'),'evidenceFilename':fr.get('filename'),'evidenceTransport':tr})
       break
     except Exception as e:
      errors+=1;rec['attempts'].append({'form':fr.get('form'),'dateFiled':fr.get('dateFiled'),'filename':fr.get('filename'),'error':type(e).__name__})
    if rec['classification']!='UNKNOWN': break
    time.sleep(.01)
  if rec['classification']!='UNKNOWN':
   resolved+=1;us+=rec['classification']=='US';nonus+=rec['classification']=='NON_US'
  results.append(rec)
  if (i+1)%100==0: print('PROGRESS',json.dumps({'done':i+1,'resolved':resolved,'errors':errors}),flush=True)
 out={'purpose':'Return-independent PIT recovery of strict-country UNKNOWN identities using only official SEC accession index-headers pages. Classification requires historical exact issuer-form name -> exactly one CIK in pre-report-date SEC master index, then matching COMPANY DATA name+CIK+STATE OF INCORPORATION in the same historical accession header. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','inputUnknownCount':len(unknown),'historicalExactUniqueCikCount':sum(r['historicalExactCik'] is not None for r in results),'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'remainingUnknownCount':len(unknown)-resolved,'transportErrorCount':errors,'masterYears':years,'masterIndexTransports':transports,'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)
if __name__=='__main__':main()
