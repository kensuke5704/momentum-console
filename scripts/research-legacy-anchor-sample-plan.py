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
FORM='N-Q'

# Keep explicit ETF registrants separate from Vanguard, where ETF share classes can
# sit inside broader mutual-fund series. Do not use generic INVESCO/SPDR substrings:
# they also match municipal/closed-end funds that are not the intended ETF universe.
STRONG_ETF=re.compile(
    r'ISHARES|SELECT SECTOR SPDR|STREETTRACKS|SPDR SERIES TRUST|SPDR INDEX SHARES|'
    r'POWERSHARES EXCHANGE[- ]TRADED|INVESCO EXCHANGE[- ]TRADED|RYDEX ETF TRUST|'
    r'PROSHARES|ETF TRUST|ETF SERIES|EXCHANGE[- ]TRADED FUND', re.I)
VANGUARD=re.compile(r'^VANGUARD\b', re.I)
STRONG_PER_YEAR=6
VANGUARD_PER_YEAR=2


def download(path:Path):
    req=urllib.request.Request(DRIVE,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r,open(path,'wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b: break
            f.write(b)


def quantile_indices(n:int,k:int):
    if n<=0 or k<=0:return []
    if n<=k:return list(range(n))
    return sorted(set(round(i*(n-1)/(k-1)) for i in range(k)))


def select_stratum(rows:list[dict],k:int,stratum:str)->list[dict]:
    grouped=defaultdict(list)
    for r in sorted(rows,key=lambda x:(x['cik'],x['dateFiled'],x['filename'])):
        grouped[r['cik']].append(r)
    ciks=sorted(grouped)
    picks=[]
    for idx in quantile_indices(len(ciks),k):
        cik=ciks[idx]; filings=grouped[cik]; pick=filings[len(filings)//2]
        picks.append({**pick,'stratum':stratum,'registrantFilingCount':len(filings),
                      'selection':'lexicographic-CIK quantile within fixed stratum; median filing by date'})
    return picks


def main():
    with tempfile.TemporaryDirectory() as td:
        zp=Path(td)/'master.zip';download(zp)
        strong_by_year=defaultdict(list);vanguard_by_year=defaultdict(list)
        with zipfile.ZipFile(zp) as z:
            names=z.namelist()
            for y in ANCHOR_YEARS:
                qfiles=[n for n in names if any(f'master_{y}_QTR{q}.idx' in n for q in range(1,5))]
                for name in sorted(qfiles):
                    for line in z.read(name).decode('latin-1','replace').splitlines():
                        p=line.split('|')
                        if len(p)<5:continue
                        cik,company,form,date_filed,filename=[x.strip() for x in p[:5]]
                        if form.upper()!=FORM or not date_filed.startswith(str(y)):continue
                        row={'year':y,'cik':cik,'company':company,'form':FORM,'dateFiled':date_filed,'filename':filename}
                        if STRONG_ETF.search(company):strong_by_year[y].append(row)
                        elif VANGUARD.search(company):vanguard_by_year[y].append(row)

        plans=[]
        for y in ANCHOR_YEARS:
            strong=select_stratum(strong_by_year[y],STRONG_PER_YEAR,'STRONG_ETF_REGISTRANT')
            vg=select_stratum(vanguard_by_year[y],VANGUARD_PER_YEAR,'VANGUARD_SHARE_CLASS_CANDIDATE')
            picks=strong+vg
            plans.append({
                'year':y,
                'strongEligibleRegistrantCiks':len({r['cik'] for r in strong_by_year[y]}),
                'strongEligibleNQFilings':len(strong_by_year[y]),
                'vanguardEligibleRegistrantCiks':len({r['cik'] for r in vanguard_by_year[y]}),
                'vanguardEligibleNQFilings':len(vanguard_by_year[y]),
                'sampleCount':len(picks),'sample':picks,
            })
            print('YEAR',y,'strong',len(strong),'vanguard',len(vg),'sample',len(picks),flush=True)
            for p in picks:print(' PICK',p['stratum'],p['cik'],p['dateFiled'],p['company'][:62],flush=True)

        out={
            'purpose':'Deterministic structural anchor-year sample plan for legacy N-Q parser/mapping validation. No prices, returns, strategy outputs, or performance metrics are used.',
            'anchorYears':ANCHOR_YEARS,'form':FORM,
            'strata':{'strongEtfRegistrantPerYear':STRONG_PER_YEAR,'vanguardShareClassCandidatePerYear':VANGUARD_PER_YEAR},
            'selectionRule':'Two fixed strata. Strong ETF registrants use explicit ETF-family patterns that avoid generic Invesco/SPDR false positives. Vanguard is sampled separately because ETF share classes may live inside broader mutual-fund series. Within each stratum/year, CIKs are sorted lexicographically, evenly spaced quantile CIKs are selected, then the median N-Q filing by filing date is chosen. No parser-success or performance selection.',
            'plans':plans,
        }
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
        print('SUMMARY',json.dumps({'anchorYears':ANCHOR_YEARS,'totalSample':sum(p['sampleCount'] for p in plans)}),flush=True)

if __name__=='__main__':main()
