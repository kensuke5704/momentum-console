#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/nport-registrant-cik-probe-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
CIK_RE=re.compile(r'CENTRAL INDEX KEY:\s*(\d+)',re.I)
NAME_RE=re.compile(r'COMPANY CONFORMED NAME:\s*([^\r\n]+)',re.I)
SERIES_RE=re.compile(r'<SERIES-ID>\s*([^<\r\n]+)',re.I)

def get(url,timeout=20):
    last=None
    for u in ('https://r.jina.ai/'+url,url):
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=timeout) as r: raw=r.read(2_500_000)
            return raw.decode('utf-8','replace'),u,len(raw)
        except Exception as e:last=repr(e)
    raise RuntimeError(last or 'fetch failed')

def archive_url(acc):
    prefix=str(int(re.sub(r'\D','',acc)[:10]))
    nodash=acc.replace('-','')
    return f'https://www.sec.gov/Archives/edgar/data/{prefix}/{nodash}/{acc}.txt'

def main():
    hist=json.loads((ROOT/'data/universe-history.json').read_text())
    months=hist.get('history',[]) if isinstance(hist,dict) else hist
    feb=next(x for x in months if x.get('signalMonth')=='2020-02')
    src=feb.get('sourceFilings',[])
    idxs=sorted(set(round(i*(len(src)-1)/7) for i in range(8)))
    sample=[src[i] for i in idxs]
    rows=[]
    for i,x in enumerate(sample,1):
        acc=x['accession']; url=archive_url(acc)
        try:
            text,transport,n=get(url)
            ciks=[]
            for v in CIK_RE.findall(text):
                z=v.zfill(10)
                if z not in ciks:ciks.append(z)
            names=[]
            for v in NAME_RE.findall(text):
                v=' '.join(v.split())
                if v not in names:names.append(v)
            sids=[]
            for v in SERIES_RE.findall(text):
                v=v.strip()
                if v not in sids:sids.append(v)
            row={'accession':acc,'seriesId':x.get('seriesId'),'seriesName':x.get('seriesName'),'transport':transport,'bytes':n,'centralIndexKeys':ciks[:10],'companyNames':names[:10],'seriesIdsInSubmission':sids[:30]}
        except Exception as e:
            row={'accession':acc,'seriesId':x.get('seriesId'),'seriesName':x.get('seriesName'),'error':repr(e)}
        rows.append(row);print(i,json.dumps(row),flush=True);time.sleep(.15)
    out={'sampleRule':'8 equal-quantile Production 2020-02 source filings; no strategy data used.','sourceCount':len(src),'sampleCount':len(sample),'rows':rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({'sourceCount':len(src),'sampleCount':len(sample),'fetchSuccess':sum('error' not in x for x in rows)}),flush=True)
if __name__=='__main__':main()
