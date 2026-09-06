#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT=ROOT/'data/research/country-domestic-form-validation-v29.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,application/zip,*/*','Accept-Encoding':'identity'}
DOMESTIC={'10-K','10-K/A','10-Q','10-Q/A'}
FOREIGN={'20-F','20-F/A','40-F','40-F/A','6-K','6-K/A'}


def fetch_text(url,limit=20_000_000,timeout=45):
    last=None
    for candidate in (url,'https://r.jina.ai/'+url):
        try:
            req=urllib.request.Request(candidate,headers=UA)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return r.read(limit).decode('latin-1','replace'),candidate
        except Exception as e:last=e
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')


def load_master(years):
    rows=[];transports={}
    for year in years:
        for q in range(1,5):
            base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
            try:
                req=urllib.request.Request(base+'/master.zip',headers=UA)
                with urllib.request.urlopen(req,timeout=35) as r:data=r.read(20_000_000)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    name=next(n for n in z.namelist() if n.lower().endswith('master.idx'))
                    text=z.read(name).decode('latin-1','replace');tr=base+'/master.zip'
            except Exception:
                text,tr=fetch_text(base+'/master.idx')
            transports[f'{year}Q{q}']=tr
            for line in text.splitlines():
                p=line.split('|')
                if len(p)<5 or not p[0].strip().isdigit():continue
                cik,company,form,date,filename=[x.strip() for x in p[:5]]
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):continue
                rows.append({'cik':cik.zfill(10),'company':company,'form':form.upper(),'dateFiled':date,'filename':filename})
    return rows,transports


def seed_cik(row):
    seeds=set()
    for a in row.get('attempts',[]):
        if a.get('historicalExactCikCount')==1 and a.get('seedCik'):
            seeds.add(str(a['seedCik']).zfill(10))
    if len(seeds)==1:return next(iter(seeds))
    if row.get('seedSource')=='HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME' and row.get('seedCik'):
        return str(row['seedCik']).zfill(10)
    return None


def classify_formset(forms):
    fs=set(forms)
    has_dom=bool(fs&DOMESTIC);has_for=bool(fs&FOREIGN)
    if has_dom and not has_for:return 'US_SIGNAL'
    if has_for and not has_dom:return 'NON_US_SIGNAL'
    return 'NO_SIGNAL'


def main():
    data=json.loads(SRC.read_text())
    rows=data.get('resolutionAudit',[])
    years=sorted({int(r['asOfReportDate'][:4]) for r in rows if r.get('asOfReportDate')})
    # Include the prior year because H1 2006 snapshots legitimately use 2005 evidence.
    years=sorted(set(years+[y-1 for y in years]))
    master,transports=load_master(years)
    by_cik=defaultdict(list)
    for r in master:by_cik[r['cik']].append(r)

    audits=[]
    for row in rows:
        cik=seed_cik(row);report=row.get('asOfReportDate')
        if not cik or not report:continue
        forms=sorted({r['form'] for r in by_cik.get(cik,[]) if r['dateFiled']<=report})
        signal=classify_formset(forms)
        audits.append({'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':report,'seedCik':cik,'strictClassification':row.get('classification'),'forms':forms,'signal':signal})

    validation=[r for r in audits if r['strictClassification'] in {'US','NON_US'} and r['signal']!='NO_SIGNAL']
    confusion=Counter((r['strictClassification'],r['signal']) for r in validation)
    us_sig=[r for r in validation if r['signal']=='US_SIGNAL']
    non_sig=[r for r in validation if r['signal']=='NON_US_SIGNAL']
    unknown=[r for r in audits if r['strictClassification']=='UNKNOWN']
    unknown_counts=Counter(r['signal'] for r in unknown)
    out={
        'purpose':'Outcome-independent validation of historical SEC reporting-form pattern as a possible country evidence source. Candidate US signal requires at least one pre-report-date 10-K/10-Q family filing and zero pre-report-date 20-F/40-F/6-K family filings for the already established historical exact-name unique CIK. Candidate NON-US signal is the inverse. No ranks, returns, current ticker metadata or strategy outcomes are used.',
        'domesticForms':sorted(DOMESTIC),'foreignForms':sorted(FOREIGN),'masterYears':years,'masterTransports':transports,
        'auditedCount':len(audits),'validationCount':len(validation),'confusion':{f'{k[0]}__{k[1]}':v for k,v in confusion.items()},
        'usSignalValidationCount':len(us_sig),'usSignalPrecisionVsStrict':sum(r['strictClassification']=='US' for r in us_sig)/len(us_sig) if us_sig else None,
        'nonUsSignalValidationCount':len(non_sig),'nonUsSignalPrecisionVsStrict':sum(r['strictClassification']=='NON_US' for r in non_sig)/len(non_sig) if non_sig else None,
        'unknownSignalCounts':dict(unknown_counts),'unknownCount':len(unknown),'audits':audits,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'audits','masterTransports'}},sort_keys=True),flush=True)

if __name__=='__main__':main()
