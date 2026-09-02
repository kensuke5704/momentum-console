#!/usr/bin/env python3
from __future__ import annotations

import json, re, tempfile, urllib.request, zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'research'/'legacy-anchor-sample-plan.json'
DRIVE='https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
ANCHOR_YEARS=[2006,2008,2010,2012,2014,2016,2018]
TARGET=re.compile(r'ISHARES|SELECT SECTOR SPDR|STREETTRACKS|SPDR|POWERSHARES|INVESCO|RYDEX ETF|PROSHARES|VANGUARD|ETF TRUST|ETF SERIES|EXCHANGE-TRADED',re.I)
FORM='N-Q'
SAMPLE_PER_YEAR=8


def download(path:Path):
    req=urllib.request.Request(DRIVE,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r,open(path,'wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b: break
            f.write(b)


def quantile_indices(n:int,k:int):
    if n<=k:return list(range(n))
    return sorted(set(round(i*(n-1)/(k-1)) for i in range(k)))


def main():
    with tempfile.TemporaryDirectory() as td:
        zp=Path(td)/'master.zip';download(zp)
        by_year=defaultdict(list)
        with zipfile.ZipFile(zp) as z:
            names=z.namelist()
            for y in ANCHOR_YEARS:
                qfiles=[n for n in names if any(f'master_{y}_QTR{q}.idx' in n for q in range(1,5))]
                for name in sorted(qfiles):
                    for line in z.read(name).decode('latin-1','replace').splitlines():
                        p=line.split('|')
                        if len(p)<5: continue
                        cik,company,form,date_filed,filename=[x.strip() for x in p[:5]]
                        if form.upper()!=FORM or not date_filed.startswith(str(y)) or not TARGET.search(company):continue
                        by_year[y].append({'year':y,'cik':cik,'company':company,'form':FORM,'dateFiled':date_filed,'filename':filename})
        plans=[]
        for y in ANCHOR_YEARS:
            grouped=defaultdict(list)
            for r in sorted(by_year[y],key=lambda x:(x['cik'],x['dateFiled'],x['filename'])):grouped[r['cik']].append(r)
            ciks=sorted(grouped)
            picks=[]
            for idx in quantile_indices(len(ciks),SAMPLE_PER_YEAR):
                cik=ciks[idx]; rows=grouped[cik]; pick=rows[len(rows)//2]
                picks.append({**pick,'registrantFilingCount':len(rows),'selection':'lexicographic-CIK quantile; median filing by date'})
            plans.append({'year':y,'eligibleRegistrantCiks':len(ciks),'eligibleNQFilings':len(by_year[y]),'sampleCount':len(picks),'sample':picks})
            print('YEAR',y,'ciks',len(ciks),'filings',len(by_year[y]),'sample',len(picks),flush=True)
            for p in picks:print(' PICK',p['cik'],p['dateFiled'],p['company'][:55],flush=True)
        out={'purpose':'Deterministic structural anchor-year sample plan for legacy N-Q parser/mapping validation. No prices, returns, strategy outputs, or performance metrics are used.',
             'anchorYears':ANCHOR_YEARS,'form':FORM,'samplePerYear':SAMPLE_PER_YEAR,
             'selectionRule':'Within each anchor year, filter N-Q filings by predeclared ETF-family name hints, group by CIK, sort CIKs lexicographically, select evenly spaced quantile CIKs, then choose the median filing by filing date within each selected CIK. No parser-success or performance selection.',
             'plans':plans}
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
        print('SUMMARY',json.dumps({'anchorYears':ANCHOR_YEARS,'totalSample':sum(p['sampleCount'] for p in plans)}),flush=True)

if __name__=='__main__':main()
