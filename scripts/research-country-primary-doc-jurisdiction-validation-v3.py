#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT=ROOT/'data/research/country-primary-doc-jurisdiction-validation-v3.json'
SPEC=importlib.util.spec_from_file_location('cover',ROOT/'scripts/research-country-cover-jurisdiction-validation-v29.py')
cover=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cover)
UA=cover.UA


def accession_parts(filename):
    m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',filename,re.I)
    if not m:return None
    cik=str(int(m.group(1)));acc=m.group(2);ad=acc.replace('-','')
    return cik,acc,ad


def index_url(filename):
    p=accession_parts(filename)
    if not p:return None
    cik,acc,ad=p
    return f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index.htm'


def fetch(url,limit=2_000_000,timeout=22):
    last=None
    for candidate in ('https://r.jina.ai/'+url,url):
        try:
            req=urllib.request.Request(candidate,headers=UA)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return r.read(limit).decode('latin-1','replace'),candidate
        except Exception as e:last=e
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')


def absolute_doc_url(href,idx_url):
    href=href.strip()
    if href.startswith('http://') or href.startswith('https://'):return href
    if href.startswith('/Archives/'):return 'https://www.sec.gov'+href
    return urllib.parse.urljoin(idx_url,href)


def doc_candidates(index_text,idx_url,form):
    links=[]
    # Markdown links emitted by readable SEC index pages.
    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)',index_text):
        label,href=m.group(1),m.group(2)
        if not re.search(r'(?i)\.(?:htm|html|txt)(?:\?|$)',href):continue
        lo=max(0,m.start()-350);hi=min(len(index_text),m.end()+350);ctx=index_text[lo:hi]
        score=0
        if re.search(r'(?i)\b'+re.escape(form)+r'\b',ctx):score+=10
        if re.search(r'(?i)FORM\s+'+re.escape(form),ctx):score+=5
        if re.search(r'(?i)EX-\d',ctx):score-=8
        if label.lower().startswith('ex'):score-=5
        links.append((score,absolute_doc_url(href,idx_url),ctx))
    # Raw/bare href fallback.
    for m in re.finditer(r'(?i)(?:href=["\']([^"\']+\.(?:htm|html))["\']|((?:https?://[^\s<>]+|/Archives/[^\s<>]+)\.(?:htm|html)))',index_text):
        href=m.group(1) or m.group(2)
        lo=max(0,m.start()-350);hi=min(len(index_text),m.end()+350);ctx=index_text[lo:hi]
        score=10 if re.search(r'(?i)\b'+re.escape(form)+r'\b',ctx) else 0
        if re.search(r'(?i)EX-\d',ctx):score-=8
        links.append((score,absolute_doc_url(href,idx_url),ctx))
    best={}
    for score,url,ctx in links:
        if 'index' in url.lower() or 'header' in url.lower():continue
        if url not in best or score>best[url][0]:best[url]=(score,ctx)
    out=sorted(((s,u,c) for u,(s,c) in best.items()),key=lambda x:(-x[0],x[1]))
    positive=[x for x in out if x[0]>=10]
    return positive[:3] if positive else out[:3]


def quantile_sample(arr,n):
    if not arr:return []
    n=min(n,len(arr));pos=sorted(set(min(len(arr)-1,(i*len(arr))//n) for i in range(n)));return [arr[i] for i in pos]


def main():
    data=json.loads(SRC.read_text());rows=data.get('resolutionAudit',[])
    years=sorted({int(r['asOfReportDate'][:4]) for r in rows if r.get('asOfReportDate')});years=sorted(set(years+[y-1 for y in years]))
    master,transports=cover.load_master(years);by=defaultdict(list)
    for r in master:by[r['cik']].append(r)
    candidates=[]
    for row in rows:
        cik=cover.seed_cik(row);report=row.get('asOfReportDate')
        if not cik or not report:continue
        filing=cover.choose_filing(by,cik,report)
        if filing:candidates.append((row,cik,filing))
    resolved=[x for x in candidates if x[0].get('classification') in {'US','NON_US'}]
    unknown=[x for x in candidates if x[0].get('classification')=='UNKNOWN']
    key=lambda x:(x[0].get('ticker') or '',x[0].get('securityId') or '',x[0].get('asOfReportDate') or '')
    resolved.sort(key=key);unknown.sort(key=key)
    sample=quantile_sample(resolved,240)+quantile_sample(unknown,240)

    # Phase 1: accession index pages.
    idx_urls=sorted({index_url(f['filename']) for _,_,f in sample if index_url(f['filename'])})
    idx_data={}
    def getone(u):
        try:t,tr=fetch(u,800_000);return u,{'text':t,'transport':tr}
        except Exception as e:return u,{'error':type(e).__name__}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i,fut in enumerate(as_completed([ex.submit(getone,u) for u in idx_urls]),1):
            u,res=fut.result();idx_data[u]=res
            if i%50==0:print('INDEX_PROGRESS',json.dumps({'done':i,'total':len(idx_urls)}),flush=True)

    selection=[];doc_urls=set()
    for row,cik,filing in sample:
        iu=index_url(filing['filename']);got=idx_data.get(iu,{})
        rec={'row':row,'cik':cik,'filing':filing,'indexUrl':iu,'indexTransport':got.get('transport'),'indexError':got.get('error'),'docs':[]}
        if got.get('text'):
            rec['docs']=doc_candidates(got['text'],iu,filing['form'])
            for _,u,_ in rec['docs']:doc_urls.add(u)
        selection.append(rec)

    # Phase 2: only selected primary-document candidates.
    docs={}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i,fut in enumerate(as_completed([ex.submit(getone,u) for u in sorted(doc_urls)]),1):
            u,res=fut.result();docs[u]=res
            if i%50==0:print('DOC_PROGRESS',json.dumps({'done':i,'total':len(doc_urls)}),flush=True)

    audits=[]
    for s in selection:
        row,cik,filing=s['row'],s['cik'],s['filing']
        rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'seedCik':cik,'strictClassification':row.get('classification'),'form':filing['form'],'dateFiled':filing['dateFiled'],'filename':filing['filename'],'indexUrl':s['indexUrl'],'indexTransport':s['indexTransport'],'indexError':s['indexError'],'documentAttempts':[]}
        hits=[]
        for score,u,_ in s['docs']:
            got=docs.get(u,{})
            one={'score':score,'documentUrl':u,'transport':got.get('transport'),'error':got.get('error')}
            if got.get('text'):
                value,cls=cover.parse_cover(got['text']);one.update({'jurisdiction':value,'coverClassification':cls})
                if cls:hits.append((value,cls,u))
            rec['documentAttempts'].append(one)
        classes=sorted({c for _,c,_ in hits})
        if len(classes)==1:
            vals=sorted({v for v,c,_ in hits if c==classes[0]})
            rec.update({'jurisdiction':vals[0] if vals else None,'coverClassification':classes[0],'resolutionSource':'PIT_PRIMARY_FILING_COVER_JURISDICTION'})
        elif len(classes)>1:rec['conflictClasses']=classes
        audits.append(rec)

    validated=[r for r in audits if r.get('strictClassification') in {'US','NON_US'} and r.get('coverClassification')]
    confusion=Counter((r['strictClassification'],r['coverClassification']) for r in validated)
    unknown_a=[r for r in audits if r.get('strictClassification')=='UNKNOWN']
    out={'purpose':'Return-independent validation of explicit jurisdiction-of-incorporation text from the primary HTML document selected through the pre-report-date SEC accession index. Historical identity is already bound to a unique CIK. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','masterYears':years,'masterTransports':transports,'candidateCount':len(candidates),'resolvedCandidateCount':len(resolved),'unknownCandidateCount':len(unknown),'sampleCount':len(audits),'uniqueIndexFetchCount':len(idx_urls),'uniqueDocumentFetchCount':len(doc_urls),'indexErrorCount':sum(bool(v.get('error')) for v in idx_data.values()),'documentErrorCount':sum(bool(v.get('error')) for v in docs.values()),'validationCount':len(validated),'confusion':{f'{a}__{b}':n for (a,b),n in confusion.items()},'validationAccuracy':sum(r['strictClassification']==r['coverClassification'] for r in validated)/len(validated) if validated else None,'unknownSampleCount':len(unknown_a),'unknownRecoveredCount':sum(bool(r.get('coverClassification')) for r in unknown_a),'unknownRecoveredUSCount':sum(r.get('coverClassification')=='US' for r in unknown_a),'unknownRecoveredNonUSCount':sum(r.get('coverClassification')=='NON_US' for r in unknown_a),'conflictCount':sum(bool(r.get('conflictClasses')) for r in audits),'audits':audits}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'audits','masterTransports'}},sort_keys=True),flush=True)

if __name__=='__main__':main()
