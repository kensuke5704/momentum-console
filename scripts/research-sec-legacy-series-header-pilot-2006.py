#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.request
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-legacy-series-header-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
FORMS={'N-Q','N-CSR','N-CSRS'}
BASE='https://www.sec.gov/Archives/edgar/full-index/2006/QTR{q}/master.idx'

def get(url,limit=8_000_000,timeout=90):
    last=None
    for u in (url,'https://r.jina.ai/'+url):
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=timeout) as r: return r.read(limit).decode('latin-1','replace'),u
        except Exception as e:last=repr(e)
    raise RuntimeError(last or 'fetch failed')

def index_rows():
    rows=[]; transports={}
    for q in range(1,5):
        text,tr=get(BASE.format(q=q));transports[str(q)]=tr
        for line in text.splitlines():
            p=line.split('|')
            if len(p)<5:continue
            cik,company,form,date,filename=[x.strip() for x in p[:5]]
            if form.upper() in FORMS and date.startswith('2006'):
                rows.append({'cik':cik,'company':company,'form':form.upper(),'dateFiled':date,'filename':filename})
    return sorted(rows,key=lambda x:(x['dateFiled'],x['cik'],x['filename'])),transports

def parse_series(text):
    # SGML registered-series blocks are filing metadata, not portfolio-content selection.
    blocks=re.findall(r'<SERIES>(.*?)(?=<SERIES>|</SERIES>|<OWNER-CIK>|<FILING-VALUES>|<DOCUMENT>|$)',text,re.I|re.S)
    out=[]
    for b in blocks:
        sid=re.search(r'<SERIES-ID>\s*([^\s<]+)',b,re.I); name=re.search(r'<SERIES-NAME>\s*([^\r\n<]+)',b,re.I)
        if not sid:continue
        tickers=re.findall(r'<TICKER-SYMBOL>\s*([^\s<]+)',b,re.I)
        classes=re.findall(r'<CLASS-CONTRACT-ID>\s*([^\s<]+)',b,re.I)
        out.append({'seriesId':sid.group(1).strip(),'seriesName':name.group(1).strip() if name else None,'tickers':sorted(set(t.strip().upper() for t in tickers)),'classContractIds':sorted(set(c.strip() for c in classes))})
    return out

def main():
    rows,transports=index_rows(); n=len(rows)
    # 16 deterministic equal-quantile filings; no company/form/holdings selection.
    pos=sorted(set(min(n-1,(i*n)//16) for i in range(16))) if n else []
    samples=[rows[i] for i in pos];results=[]
    for i,r in enumerate(samples,1):
        url='https://www.sec.gov/Archives/'+r['filename'].lstrip('/')
        try:
            text,tr=get(url,4_000_000,45); series=parse_series(text)
            result={**r,'transport':tr,'seriesCount':len(series),'seriesWithTicker':sum(bool(s['tickers']) for s in series),'series':series[:50]}
        except Exception as e: result={**r,'error':repr(e),'seriesCount':0,'seriesWithTicker':0,'series':[]}
        results.append(result);print('SAMPLE',json.dumps({k:result.get(k) for k in ['company','form','dateFiled','seriesCount','seriesWithTicker','error']}),flush=True)
        time.sleep(.15)
    formcounts=Counter(r['form'] for r in rows); companies=len({(r['cik'],r['company']) for r in rows})
    ok=[r for r in results if 'error' not in r]
    out={'year':2006,'purpose':'Feasibility pilot for Production-independent legacy source discovery from official SEC quarterly master indexes and registered-series SGML headers. Filing samples are deterministic equal-quantile positions; no holdings, Universe ranks, or returns used.','masterIndexTransports':transports,'targetFilingCount':n,'targetRegistrantCount':companies,'formCounts':dict(formcounts),'sampleCount':len(samples),'fetchSuccess':len(ok),'sampleWithSeriesHeader':sum(r['seriesCount']>0 for r in ok),'sampleWithTickeredSeries':sum(r['seriesWithTicker']>0 for r in ok),'totalSeriesParsedInSamples':sum(r['seriesCount'] for r in ok),'totalTickeredSeriesInSamples':sum(r['seriesWithTicker'] for r in ok),'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
