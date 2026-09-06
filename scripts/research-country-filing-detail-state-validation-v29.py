#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT=ROOT/'data/research/country-filing-detail-state-validation-v29.json'
SPEC=importlib.util.spec_from_file_location('cover',ROOT/'scripts/research-country-cover-jurisdiction-validation-v29.py')
cover=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cover)
UA=cover.UA
US_CODES=cover.US_CODES|{'X1'}


def accession_parts(filename):
    m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',filename,re.I)
    if not m:return None
    cik=str(int(m.group(1)));acc=m.group(2);ad=acc.replace('-','')
    return cik,acc,ad


def detail_url(filename):
    p=accession_parts(filename)
    if not p:return None
    cik,acc,ad=p
    return f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index.htm'


def fetch(url,limit=800_000,timeout=20):
    last=None
    for candidate in ('https://r.jina.ai/'+url,url):
        try:
            req=urllib.request.Request(candidate,headers=UA)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return r.read(limit).decode('latin-1','replace'),candidate
        except Exception as e:last=e
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')


def state_for_cik(text,cik):
    z=str(cik).zfill(10);states=[]
    # Jina/SEC rendered Filing Detail generally prints:
    # NAME (Filer) CIK: 0000123456 ... State of Incorp.: DE
    patterns=[
      rf'(?is)CIK\s*:\s*0*{int(z)}\b(.{{0,1800}}?)(?:State\s+of\s+Incorp\.?|State\s+of\s+Incorporation)\s*:\s*([A-Z0-9]{{2,3}})\b',
      rf'(?is)CIK=0*{int(z)}\b(.{{0,1800}}?)(?:State\s+of\s+Incorp\.?|State\s+of\s+Incorporation)\s*:\s*([A-Z0-9]{{2,3}})\b',
    ]
    for p in patterns:
        for m in re.finditer(p,text):states.append(m.group(2).upper())
    # Reverse ordering fallback: state field may precede a linked CIK in rendered markdown.
    for m in re.finditer(r'(?is)(?:State\s+of\s+Incorp\.?|State\s+of\s+Incorporation)\s*:\s*([A-Z0-9]{2,3})\b(.{0,1800}?)CIK\s*:\s*0*(\d{1,10})\b',text):
        if m.group(3).zfill(10)==z:states.append(m.group(1).upper())
    uniq=sorted(set(states))
    return uniq[0] if len(uniq)==1 else None


def quantile_sample(arr,n):
    if not arr:return []
    n=min(n,len(arr));positions=sorted(set(min(len(arr)-1,(i*len(arr))//n) for i in range(n)));return [arr[i] for i in positions]


def main():
    data=json.loads(SRC.read_text());rows=data.get('resolutionAudit',[])
    years=sorted({int(r['asOfReportDate'][:4]) for r in rows if r.get('asOfReportDate')});years=sorted(set(years+[y-1 for y in years]))
    master,transports=cover.load_master(years);by=defaultdict(list)
    for r in master:by[r['cik']].append(r)
    candidates=[]
    for row in rows:
        cik=cover.seed_cik(row);report=row.get('asOfReportDate')
        if not cik or not report:continue
        filing=cover.choose_filing(by,cik,report)
        if filing:candidates.append((row,cik,filing))
    resolved=[x for x in candidates if x[0].get('classification') in {'US','NON_US'}]
    unknown=[x for x in candidates if x[0].get('classification')=='UNKNOWN']
    key=lambda x:(x[0].get('ticker') or '',x[0].get('securityId') or '',x[0].get('asOfReportDate') or '')
    resolved.sort(key=key);unknown.sort(key=key)
    sample=quantile_sample(resolved,240)+quantile_sample(unknown,240)
    urls=sorted({detail_url(f['filename']) for _,_,f in sample if detail_url(f['filename'])})
    fetched={}
    def one(u):
        try:t,tr=fetch(u);return u,{'text':t,'transport':tr}
        except Exception as e:return u,{'error':type(e).__name__}
    # Low parallelism avoids SEC/Jina throttling while still removing serial latency.
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i,fut in enumerate(as_completed([ex.submit(one,u) for u in urls]),1):
            u,res=fut.result();fetched[u]=res
            if i%50==0:print('FETCH_PROGRESS',json.dumps({'done':i,'total':len(urls)}),flush=True)
    audits=[]
    for row,cik,filing in sample:
        u=detail_url(filing['filename']);got=fetched.get(u,{})
        rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'seedCik':cik,'strictClassification':row.get('classification'),'form':filing['form'],'dateFiled':filing['dateFiled'],'filename':filing['filename'],'detailUrl':u,'transport':got.get('transport'),'error':got.get('error')}
        if got.get('text'):
            state=state_for_cik(got['text'],cik)
            if state:rec.update({'stateCode':state,'detailClassification':'US' if state in US_CODES else 'NON_US','resolutionSource':'PIT_EDGAR_FILING_DETAIL_CIK_STATE'})
        audits.append(rec)
    validated=[r for r in audits if r.get('strictClassification') in {'US','NON_US'} and r.get('detailClassification')]
    confusion=Counter((r['strictClassification'],r['detailClassification']) for r in validated)
    unknown_a=[r for r in audits if r.get('strictClassification')=='UNKNOWN']
    out={'purpose':'Return-independent validation of EDGAR Filing Detail State of Incorp. bound to the already established historical unique CIK on a pre-report-date filing. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','masterYears':years,'masterTransports':transports,'candidateCount':len(candidates),'resolvedCandidateCount':len(resolved),'unknownCandidateCount':len(unknown),'sampleCount':len(audits),'uniqueFetchCount':len(urls),'fetchErrorCount':sum(bool(v.get('error')) for v in fetched.values()),'validationCount':len(validated),'confusion':{f'{a}__{b}':n for (a,b),n in confusion.items()},'validationAccuracy':sum(r['strictClassification']==r['detailClassification'] for r in validated)/len(validated) if validated else None,'unknownSampleCount':len(unknown_a),'unknownRecoveredCount':sum(bool(r.get('detailClassification')) for r in unknown_a),'unknownRecoveredUSCount':sum(r.get('detailClassification')=='US' for r in unknown_a),'unknownRecoveredNonUSCount':sum(r.get('detailClassification')=='NON_US' for r in unknown_a),'audits':audits}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'audits','masterTransports'}},sort_keys=True),flush=True)

if __name__=='__main__':main()
