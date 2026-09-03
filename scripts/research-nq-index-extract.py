#!/usr/bin/env python3
from __future__ import annotations
import json, time, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
OUT=ROOT/'data'/'research'/'nq-index-2006.json'
TARGET_FORMS={'N-Q','N-Q/A','N-CSR','N-CSRS','N-CSR/A','N-CSRS/A'}
BASE='https://www.sec.gov/Archives/edgar/full-index/2006/QTR{q}/master.idx'

def plausible_index(text:str)->bool:
    lines=[line for line in text.splitlines() if '|' in line]
    return len(lines)>1000 and any(line.startswith('CIK|') for line in lines[:100])

def fetch_text(url:str,attempts:int=3)->tuple[str,str]:
    candidates=[url,'https://r.jina.ai/'+url]
    last_error=None
    for candidate in candidates:
        for attempt in range(1,attempts+1):
            try:
                req=urllib.request.Request(candidate,headers=UA)
                with urllib.request.urlopen(req,timeout=180) as r:
                    data=r.read()
                if len(data)<100_000:
                    raise ValueError(f'index response too small: bytes={len(data):,}')
                text=data.decode('latin-1','replace')
                if not plausible_index(text):
                    raise ValueError('unexpected SEC master.idx format')
                print(f'fetch {candidate} bytes={len(data):,} attempt={attempt}',flush=True)
                return text,candidate
            except Exception as e:
                last_error=e
                print(f'fetch attempt {attempt}/{attempts} failed for {candidate}: {e!r}',flush=True)
                if attempt<attempts: time.sleep(2.0*attempt)
    raise RuntimeError(f'unable to fetch SEC master index through direct or proxy route: {url}') from last_error

def main():
    hits=[]; quarter_sources=[]
    for q in range(1,5):
        url=BASE.format(q=q); text,transport=fetch_text(url); count=0
        quarter_sources.append({'officialUrl':url,'transportUrl':transport})
        for line in text.splitlines():
            p=line.split('|')
            if len(p)<5: continue
            cik,company,form,date_filed,filename=[x.strip() for x in p[:5]]
            if form.upper() not in TARGET_FORMS or not date_filed.startswith('2006'): continue
            hits.append({'cik':cik,'company':company,'form':form.upper(),'dateFiled':date_filed,'filename':filename}); count+=1
        print(f'QTR{q} hits={count}',flush=True)
    uniq={(x['cik'],x['form'],x['dateFiled'],x['filename']):x for x in hits}
    hits=sorted(uniq.values(),key=lambda x:(x['dateFiled'],x['cik'],x['form'],x['filename']))
    form_counts={}; month_counts={}
    for x in hits:
        form_counts[x['form']]=form_counts.get(x['form'],0)+1
        m=x['dateFiled'][:7]; month_counts[m]=month_counts.get(m,0)+1
    summary={'source':'Official SEC EDGAR quarterly full-index master.idx; transport may use r.jina.ai when SEC blocks GitHub-hosted runners','sourceUrls':quarter_sources,'targetYear':2006,'targetForms':sorted(TARGET_FORMS),'hitCount':len(hits),'formCounts':form_counts,'monthCounts':month_counts,'filings':hits}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='filings'}),flush=True)

if __name__=='__main__': main()
