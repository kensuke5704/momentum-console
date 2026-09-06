#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT = ROOT / 'data/research/country-foreign-form-recovery-v29.json'
UA = {'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,*/*','Accept-Encoding':'identity'}

# These forms are available only to foreign private issuers / foreign issuers under SEC rules.
# 20-F and 40-F are annual-registration/reporting forms; 6-K is the foreign-private-issuer current report.
# F-series registration statements are kept diagnostic-only below; automatic classification uses the
# strongest reporting forms only to avoid broadening the country rule unnecessarily.
STRONG_FOREIGN_FORMS = {'20-F','20-F/A','40-F','40-F/A','6-K','6-K/A'}
DIAGNOSTIC_FOREIGN_FORMS = {'F-1','F-1/A','F-3','F-3/A','F-4','F-4/A','F-6','F-6/A'}
JURIS_RE = re.compile(r'\s*/[A-Z0-9]{2,3}/?\s*$', re.I)


def clean_issuer(s: str) -> str:
    s = re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$', '', s or '', flags=re.I)
    return ' '.join(s.replace('’', "'").split()).strip(' .,-')


def normalize_company(s: str) -> str:
    s = JURIS_RE.sub('', s or '')
    s = clean_issuer(s).upper().replace('&', ' AND ')
    s = re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b', ' ', s)
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


def cleaned_forms(raw: str) -> list[str]:
    vals=[raw]; s=raw
    pats=[
        r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',
        r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',
        r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',
        r'\s*/[A-Z]{2}\s*$',
    ]
    changed=True
    while changed:
        changed=False
        for p in pats:
            ns=re.sub(p,'',s,flags=re.I).strip()
            if ns != s:
                vals.append(ns); s=ns; changed=True
    return list(dict.fromkeys(v for v in vals if v))


def load_master(years: list[int]):
    rows=[]; transports={}
    for year in years:
        for q in range(1,5):
            base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
            text=None; transport=None
            try:
                req=urllib.request.Request(base+'/master.zip',headers=UA)
                with urllib.request.urlopen(req,timeout=35) as r:
                    data=r.read(20_000_000)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    name=next(n for n in z.namelist() if n.lower().endswith('master.idx'))
                    text=z.read(name).decode('latin-1','replace')
                transport=base+'/master.zip'
            except Exception:
                url='https://r.jina.ai/'+base+'/master.idx'
                req=urllib.request.Request(url,headers=UA)
                with urllib.request.urlopen(req,timeout=45) as r:
                    text=r.read(20_000_000).decode('latin-1','replace')
                transport=url
            transports[f'{year}Q{q}']=transport
            for line in text.splitlines():
                p=line.split('|')
                if len(p)<5 or not p[0].strip().isdigit():
                    continue
                cik,company,form,date,filename=[x.strip() for x in p[:5]]
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):
                    continue
                rows.append({'cik':cik.zfill(10),'company':company,'normalizedCompany':normalize_company(company),'form':form.upper(),'dateFiled':date,'filename':filename})
    return rows, transports


def main():
    data=json.loads(SRC.read_text())
    unknown=[r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN']
    years=sorted({int(r['asOfReportDate'][:4]) for r in unknown if r.get('asOfReportDate')})
    master, transports=load_master(years)
    by_name=defaultdict(list)
    for r in master:
        by_name[r['normalizedCompany']].append(r)

    results=[]; counts=Counter(); conflicts=0
    for row in unknown:
        report=row.get('asOfReportDate')
        forms=[]
        for issuer in row.get('issuerVariants',[]):
            for f in cleaned_forms(str(issuer)):
                if f and f not in forms:
                    forms.append(f)
        exact_rows=[]
        for f in forms:
            exact_rows.extend(r for r in by_name.get(normalize_company(f),[]) if report and r['dateFiled']<=report)
        # same historical exact-name evidence must identify exactly one CIK across all cleaned forms
        by_cik=defaultdict(list)
        for r in exact_rows:
            by_cik[r['cik']].append(r)
        rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':report,'issuerVariants':row.get('issuerVariants',[]),'historicalExactCikCount':len(by_cik),'historicalExactCiks':sorted(by_cik)[:8],'classification':'UNKNOWN'}
        if len(by_cik)==1:
            cik=next(iter(by_cik)); rows=by_cik[cik]
            strong=sorted({r['form'] for r in rows if r['form'] in STRONG_FOREIGN_FORMS})
            diagnostic=sorted({r['form'] for r in rows if r['form'] in DIAGNOSTIC_FOREIGN_FORMS})
            rec.update({'seedCik':cik,'strongForeignForms':strong,'diagnosticForeignForms':diagnostic})
            if strong:
                rec.update({'classification':'NON_US','resolutionSource':'PIT_SEC_MASTER_STRONG_FOREIGN_ISSUER_FORM','evidenceForms':strong})
        counts[rec['classification']]+=1
        results.append(rec)
    out={
        'purpose':'Return-independent PIT recovery for strict-country UNKNOWN identities using only official SEC historical master indexes. Automatic NON_US classification requires historical cleaned exact issuer-form name -> exactly one CIK before the report date and at least one strong foreign-private-issuer reporting form (20-F, 40-F or 6-K, including amendments). F-series registration forms are diagnostic only. No current ticker metadata, current country/state, fuzzy matching, US default, ranks, returns or strategy outcomes are used.',
        'inputUnknownCount':len(unknown),
        'resolvedNonUSCount':counts['NON_US'],
        'remainingUnknownCount':counts['UNKNOWN'],
        'masterYears':years,
        'masterIndexTransports':transports,
        'results':results,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)

if __name__=='__main__':
    main()
