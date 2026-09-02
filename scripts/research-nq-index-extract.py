#!/usr/bin/env python3
from __future__ import annotations
import json, tempfile, urllib.request, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DRIVE='https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
OUT=ROOT/'data'/'research'/'nq-index-2006.json'
TARGET_FORMS={'N-Q','N-Q/A','N-CSR','N-CSRS','N-CSR/A','N-CSRS/A'}

def download(url:str,path:Path):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r, open(path,'wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b: break
            f.write(b)
    print(f'download complete bytes={path.stat().st_size:,}',flush=True)

def main():
    with tempfile.TemporaryDirectory() as td:
        zp=Path(td)/'master.zip'; download(DRIVE,zp)
        with zipfile.ZipFile(zp) as z:
            names=z.namelist()
            qfiles=[n for n in names if any(f'master_2006_QTR{q}.idx' in n for q in range(1,5))]
            print('2006 quarter files=',qfiles,flush=True)
            hits=[]
            for name in sorted(qfiles):
                text=z.read(name).decode('latin-1','replace')
                count=0
                for line in text.splitlines():
                    p=line.split('|')
                    if len(p)<5: continue
                    cik,company,form,date_filed,filename=[x.strip() for x in p[:5]]
                    if form.upper() not in TARGET_FORMS or not date_filed.startswith('2006'): continue
                    hits.append({'cik':cik,'company':company,'form':form,'dateFiled':date_filed,'filename':filename}); count+=1
                print(name,'hits=',count,flush=True)
            uniq={(x['cik'],x['form'],x['dateFiled'],x['filename']):x for x in hits}
            hits=sorted(uniq.values(),key=lambda x:(x['dateFiled'],x['cik'],x['form'],x['filename']))
            form_counts={}; month_counts={}
            for x in hits:
                form_counts[x['form']]=form_counts.get(x['form'],0)+1
                m=x['dateFiled'][:7]; month_counts[m]=month_counts.get(m,0)+1
            summary={'archiveBytes':zp.stat().st_size,'targetYear':2006,'quarterFiles':qfiles,'targetForms':sorted(TARGET_FORMS),'hitCount':len(hits),'formCounts':form_counts,'monthCounts':month_counts,'filings':hits}
            OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(summary,indent=2)+'\n')
            print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='filings'}),flush=True)
            print('FIRST_HITS',json.dumps(hits[:10],indent=2),flush=True)

if __name__=='__main__': main()
