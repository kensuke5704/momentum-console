#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, tempfile, time, urllib.request, zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DRIVE='https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
OUT=ROOT/'data'/'research'/'nq-bridge-parser-2019.json'
TARGET={'N-Q','N-Q/A','N-CSR','N-CSR/A','N-CSRS','N-CSRS/A'}

spec=importlib.util.spec_from_file_location('nqpilot',ROOT/'scripts'/'research-nq-parser-pilot.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def download(path:Path):
    req=urllib.request.Request(DRIVE,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r,open(path,'wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b:break
            f.write(b)

def index_2019():
    with tempfile.TemporaryDirectory() as td:
        zp=Path(td)/'master.zip';download(zp)
        hits=[]
        with zipfile.ZipFile(zp) as z:
            qfiles=[n for n in z.namelist() if any(f'master_2019_QTR{q}.idx' in n for q in range(1,5))]
            for name in sorted(qfiles):
                text=z.read(name).decode('latin-1','replace')
                for line in text.splitlines():
                    p=line.split('|')
                    if len(p)<5:continue
                    cik,company,form,date_filed,filename=[x.strip() for x in p[:5]]
                    if form.upper() in TARGET and date_filed.startswith('2019-'):
                        hits.append({'cik':cik,'company':company,'form':form,'dateFiled':date_filed,'filename':filename})
    return hits

def samples(filings):
    by=defaultdict(list)
    for x in filings:
        if x['form']=='N-Q':by[x['dateFiled'][:7]].append(x)
    out=[]
    for month,rows in sorted(by.items()):
        idxs=sorted(set([len(rows)//4,len(rows)//2,(3*len(rows))//4]))
        out.extend(rows[i] for i in idxs)
    return out

def main():
    filings=index_2019(); forms=defaultdict(int); form_months=defaultdict(lambda:defaultdict(int))
    for x in filings:
        forms[x['form']]+=1; form_months[x['form']][x['dateFiled'][:7]]+=1
    samp=samples(filings)
    print('2019 filings',len(filings),'forms',dict(forms),'samples',len(samp),flush=True)
    print('N-Q filing months',dict(sorted(form_months['N-Q'].items())),flush=True)
    results=[]
    for i,x in enumerate(samp,1):
        try:
            text=mod.get_text(mod.sec_url(x['filename']))
            method,hrows,plines,holdings=mod.parse_holdings(text)
            obvious_noise=sum(1 for h in holdings if h['description'].upper().startswith(('DATE:','JANUARY ','FEBRUARY ','MARCH ','APRIL ','MAY ','JUNE ','JULY ','AUGUST ','SEPTEMBER ','OCTOBER ','NOVEMBER ','DECEMBER ','OTHER ASSETS')))
            r={'month':x['dateFiled'][:7],'company':x['company'],'cik':x['cik'],'dateFiled':x['dateFiled'],'filename':x['filename'],'method':method,'parsedHoldings':len(holdings),'obviousNoiseRows':obvious_noise,'noiseRate':obvious_noise/len(holdings) if holdings else 0,'positiveValues':sum(h['marketValue']>0 for h in holdings),'sampleHoldings':holdings[:8]}
            print(f"{i}/{len(samp)} {r['month']} {x['company'][:34]} {method} holdings={len(holdings)} noise={r['noiseRate']:.3f}",flush=True)
        except Exception as e:
            r={'month':x['dateFiled'][:7],'company':x['company'],'filename':x['filename'],'error':repr(e)};print(i,'FAIL',repr(e),flush=True)
        results.append(r);time.sleep(.1)
    ok=[r for r in results if 'error' not in r]
    def rate(fn):return sum(1 for r in ok if fn(r))/len(ok) if ok else None
    counts=sorted(r['parsedHoldings'] for r in ok)
    summary={'year':2019,'allTargetFilings':len(filings),'formCounts':dict(forms),'formMonthCounts':{f:dict(sorted(m.items())) for f,m in form_months.items()},'nqFilingMonths':dict(sorted(form_months['N-Q'].items())),'sampleRule':'Three deterministic N-Q filings per filing month at 25/50/75 percent index positions.','sampleCount':len(samp),'fetchSuccess':len(ok),'fetchRate':len(ok)/len(samp) if samp else None,'atLeast10HoldingsRate':rate(lambda r:r['parsedHoldings']>=10),'atLeast20HoldingsRate':rate(lambda r:r['parsedHoldings']>=20),'atLeast50HoldingsRate':rate(lambda r:r['parsedHoldings']>=50),'lowNoiseAnd20Rate':rate(lambda r:r['parsedHoldings']>=20 and r['noiseRate']<=.05),'medianParsedHoldings':counts[len(counts)//2] if counts else None,'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)

if __name__=='__main__':main()
