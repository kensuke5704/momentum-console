#!/usr/bin/env python3
from __future__ import annotations
import io, json, re, urllib.request, zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'research'/'legacy-fund-filings-2006.json'
URL='https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'application/octet-stream'}
TARGET_FORMS={'N-Q','N-Q/A','N-CSR','N-CSR/A','N-CSRS','N-CSRS/A'}

def download()->bytes:
    req=urllib.request.Request(URL,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r:
        chunks=[]; total=0
        while True:
            b=r.read(1024*1024)
            if not b: break
            chunks.append(b); total+=len(b)
            if total%(50*1024*1024)<1024*1024: print(f'downloaded={total/1024/1024:.1f} MiB',flush=True)
        return b''.join(chunks)

def parse_idx(text:str,qtr:int):
    rows=[]
    for ln in text.splitlines():
        if not re.match(r'^\d+\|',ln): continue
        p=ln.split('|')
        if len(p)<5: continue
        cik,name,form,filed,filename=p[:5]
        if form not in TARGET_FORMS: continue
        rows.append({'cik':cik,'companyName':name,'form':form,'filed':filed,'filename':filename,'quarter':qtr})
    return rows

def main():
    payload=download(); print(f'zip_bytes={len(payload):,}',flush=True)
    allrows=[]; names=[]
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names=z.namelist()
        for q in range(1,5):
            candidates=[n for n in names if re.search(fr'master[_-]?2006[_-]?QTR{q}\.idx$',n,re.I)]
            if not candidates:
                candidates=[n for n in names if '2006' in n and f'QTR{q}' in n.upper() and n.lower().endswith('.idx')]
            print('qtr',q,'candidates',candidates[:5],flush=True)
            if not candidates: continue
            text=z.read(candidates[0]).decode('latin1','replace')
            rows=parse_idx(text,q); allrows.extend(rows)
            print('qtr',q,'targetFilings',len(rows),Counter(r['form'] for r in rows),flush=True)
    byform=Counter(r['form'] for r in allrows)
    bymonth=Counter(r['filed'][:7] for r in allrows)
    unique_ciks=len({r['cik'] for r in allrows})
    out={'source':'University of Notre Dame SRAF MasterIndex_20260318.zip, derived from SEC EDGAR master.idx','year':2006,'targetForms':sorted(TARGET_FORMS),'filings':len(allrows),'uniqueCiks':unique_ciks,'byForm':dict(byform),'byMonth':dict(sorted(bymonth.items())),'sample':allrows[:40],'rows':allrows}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('rows','sample')}),flush=True)

if __name__=='__main__': main()
