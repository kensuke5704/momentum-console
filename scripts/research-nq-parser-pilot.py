#!/usr/bin/env python3
from __future__ import annotations
import json, re, time, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IDX=ROOT/'data'/'research'/'nq-index-2006.json'
OUT=ROOT/'data'/'research'/'nq-parser-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain'}
CUSIP_RE=re.compile(r'(?<![A-Z0-9])([0-9A-Z*@#]{6}[0-9A-Z*@#]{2}[0-9A-Z*@#])(?![A-Z0-9])')

def sec_url(filename:str)->str:
    # master.idx filenames are already rooted at edgar/, e.g.
    # edgar/data/1000069/0001000069-06-000006.txt.  Preserve that prefix.
    return 'https://www.sec.gov/Archives/'+filename.lstrip('/')

def get_text(url:str)->str:
    req=urllib.request.Request('https://r.jina.ai/'+url,headers=UA)
    with urllib.request.urlopen(req,timeout=180) as r:return r.read(4_000_000).decode('utf-8','replace')

def sample_filings(filings):
    by=defaultdict(list)
    for x in filings:
        if x['form']!='N-Q':continue
        by[x['dateFiled'][:7]].append(x)
    out=[]
    for month in sorted(by):
        rows=by[month]
        # deterministic spread within month, no cherry-picking by filer/content
        picks=[rows[0]] if len(rows)==1 else [rows[len(rows)//3],rows[(2*len(rows))//3]]
        out.extend(picks)
    return out

def context_lines(text:str,cusips:list[str],limit=8):
    lines=text.splitlines(); out=[]
    wanted=set(cusips[:20])
    for i,line in enumerate(lines):
        if any(c in line for c in wanted):
            out.append(' | '.join(x.strip() for x in lines[max(0,i-1):min(len(lines),i+2)] if x.strip())[:600])
            if len(out)>=limit:break
    return out

def main():
    idx=json.loads(IDX.read_text()); samples=sample_filings(idx['filings'])
    print('sample filings=',len(samples),flush=True)
    results=[]
    for i,x in enumerate(samples,1):
        url=sec_url(x['filename'])
        try:
            text=get_text(url); upper=text.upper()
            cusips=sorted(set(CUSIP_RE.findall(upper)))
            lines=upper.splitlines(); near=set()
            for j,line in enumerate(lines):
                if any(k in line for k in ('CUSIP','PORTFOLIO','SECURITIES','SHARES','VALUE')):
                    block=' '.join(lines[max(0,j-2):min(len(lines),j+3)])
                    near.update(CUSIP_RE.findall(block))
            r={'month':x['dateFiled'][:7],'cik':x['cik'],'company':x['company'],'dateFiled':x['dateFiled'],'filename':x['filename'],'url':url,'bytes':len(text.encode()),'hasPortfolio':('PORTFOLIO' in upper),'hasSchedule':('SCHEDULE OF INVESTMENTS' in upper),'hasCusipWord':('CUSIP' in upper),'uniqueCusipLike':len(cusips),'uniqueCusipNearHoldingVocabulary':len(near),'sampleCusips':cusips[:15],'contexts':context_lines(text,cusips)}
            print(f"{i}/{len(samples)} {r['month']} {x['company'][:35]} bytes={r['bytes']} cusip={r['uniqueCusipLike']} near={r['uniqueCusipNearHoldingVocabulary']} portfolio={r['hasPortfolio']}",flush=True)
        except Exception as e:
            r={'month':x['dateFiled'][:7],'cik':x['cik'],'company':x['company'],'dateFiled':x['dateFiled'],'filename':x['filename'],'url':url,'error':repr(e)}
            print(i,'FAIL',repr(e),flush=True)
        results.append(r); time.sleep(0.15)
    ok=[r for r in results if 'error' not in r]
    def rate(pred):return sum(1 for r in ok if pred(r))/len(ok) if ok else None
    summary={'year':2006,'sampleRule':'Two deterministic N-Q filings per filing month (1/3 and 2/3 positions in master-index order).','sampleCount':len(samples),'fetchSuccess':len(ok),'fetchRate':len(ok)/len(samples) if samples else None,'portfolioMarkerRate':rate(lambda r:r['hasPortfolio']),'scheduleMarkerRate':rate(lambda r:r['hasSchedule']),'cusipWordRate':rate(lambda r:r['hasCusipWord']),'anyCusipLikeRate':rate(lambda r:r['uniqueCusipLike']>0),'atLeast10CusipLikeRate':rate(lambda r:r['uniqueCusipLike']>=10),'medianCusipLike':None,'results':results}
    vals=sorted(r['uniqueCusipLike'] for r in ok)
    if vals: summary['medianCusipLike']=vals[len(vals)//2]
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)

if __name__=='__main__':main()
