#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
OUT = ROOT/'data'/'research'/'legacy-development-manifest.json'
YEARS=range(2006,2011)
TARGET=re.compile(r'ISHARES|SELECT SECTOR SPDR|STREETTRACKS|SPDR|POWERSHARES|INVESCO|RYDEX ETF|PROSHARES|VANGUARD|ETF TRUST|ETF SERIES|EXCHANGE-TRADED',re.I)


def download(path:Path):
    req=urllib.request.Request(DRIVE,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r,open(path,'wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b:break
            f.write(b)


def main():
    rows=[]
    with tempfile.TemporaryDirectory() as td:
        zp=Path(td)/'master.zip';download(zp)
        with zipfile.ZipFile(zp) as z:
            names=z.namelist()
            for year in YEARS:
                qfiles=sorted(n for n in names if re.search(rf'master_{year}_QTR[1-4]\.idx$',n))
                for name in qfiles:
                    for line in z.read(name).decode('latin-1','replace').splitlines():
                        p=line.split('|')
                        if len(p)<5:continue
                        cik,company,form,date_filed,filename=[x.strip() for x in p[:5]]
                        if form.upper()!='N-Q' or not date_filed.startswith(str(year)) or not TARGET.search(company):continue
                        rows.append({'year':year,'month':date_filed[:7],'cik':cik,'company':company,'filingDate':date_filed,'filename':filename})
    uniq={(r['cik'],r['filingDate'],r['filename']):r for r in rows}
    rows=sorted(uniq.values(),key=lambda r:(r['filingDate'],r['cik'],r['filename']))
    by_year={}
    for year in YEARS:
        yr=[r for r in rows if r['year']==year]
        by_month=defaultdict(int)
        for r in yr:by_month[r['month']]+=1
        by_year[str(year)]={'candidateNqFilings':len(yr),'uniqueCiks':len({r['cik'] for r in yr}),'byMonth':dict(sorted(by_month.items()))}
    # Batch assignment is deterministic and transport-only. It does not select based on parser success.
    manifest=[]
    for i,r in enumerate(rows):manifest.append({**r,'batch':i//40+1})
    out={'purpose':'Deterministic transport manifest for full DEVELOPMENT-window legacy ETF filing reconstruction. No prices, returns, parser-success selection, or strategy metrics used.',
         'years':[2006,2010],'targetRule':TARGET.pattern,'batchSize':40,'candidateFilings':len(rows),'batchCount':(len(rows)+39)//40,'byYear':by_year,'filings':manifest}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='filings'},sort_keys=True),flush=True)

if __name__=='__main__':main()
