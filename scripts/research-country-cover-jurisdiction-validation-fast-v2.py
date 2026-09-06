#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT = ROOT / 'data/research/country-cover-jurisdiction-validation-v29.json'
SPEC = importlib.util.spec_from_file_location('cover', ROOT/'scripts/research-country-cover-jurisdiction-validation-v29.py')
cover = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(cover)


def quantile_sample(arr, n):
    if not arr: return []
    n = min(n, len(arr))
    positions = sorted(set(min(len(arr)-1, (i*len(arr))//n) for i in range(n)))
    return [arr[i] for i in positions]


def main():
    data = json.loads(SRC.read_text()); rows = data.get('resolutionAudit', [])
    years = sorted({int(r['asOfReportDate'][:4]) for r in rows if r.get('asOfReportDate')})
    years = sorted(set(years + [y-1 for y in years]))
    master, transports = cover.load_master(years)
    by_cik = defaultdict(list)
    for r in master: by_cik[r['cik']].append(r)

    candidates=[]
    for row in rows:
        cik=cover.seed_cik(row); report=row.get('asOfReportDate')
        if not cik or not report: continue
        filing=cover.choose_filing(by_cik,cik,report)
        if filing: candidates.append((row,cik,filing))
    resolved=[x for x in candidates if x[0].get('classification') in {'US','NON_US'}]
    unknown=[x for x in candidates if x[0].get('classification')=='UNKNOWN']
    key=lambda x:(x[0].get('ticker') or '',x[0].get('securityId') or '',x[0].get('asOfReportDate') or '')
    resolved.sort(key=key); unknown.sort(key=key)
    sample=quantile_sample(resolved,240)+quantile_sample(unknown,240)

    urls=sorted({cover.submission_url(filing['filename']) for _,_,filing in sample})
    fetched={}
    def one(url):
        try:
            text,tr=cover.fetch_text(url)
            return url, {'text':text,'transport':tr}
        except Exception as e:
            return url, {'error':type(e).__name__}
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures=[ex.submit(one,u) for u in urls]
        for i,f in enumerate(as_completed(futures),1):
            u,res=f.result(); fetched[u]=res
            if i%50==0: print('FETCH_PROGRESS',json.dumps({'done':i,'total':len(urls)}),flush=True)

    audits=[]
    for row,cik,filing in sample:
        rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'seedCik':cik,'strictClassification':row.get('classification'),'form':filing['form'],'dateFiled':filing['dateFiled'],'filename':filing['filename']}
        url=cover.submission_url(filing['filename']); got=fetched[url]
        if 'error' in got:
            rec['error']=got['error']
        else:
            value,cls=cover.parse_cover(got['text'])
            rec.update({'transport':got['transport'],'jurisdiction':value,'coverClassification':cls})
        audits.append(rec)

    validated=[r for r in audits if r.get('strictClassification') in {'US','NON_US'} and r.get('coverClassification')]
    confusion=Counter((r['strictClassification'],r['coverClassification']) for r in validated)
    unknown_a=[r for r in audits if r.get('strictClassification')=='UNKNOWN']
    out={
        'purpose':'Return-independent validation of explicit jurisdiction-of-incorporation text on pre-report-date SEC filing cover pages. Historical issuer identity is already bound to one CIK. Fetch parallelism changes transport only; sample, filing selection and parser are identical to the preregistered validation. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.',
        'masterYears':years,'masterTransports':transports,'candidateCount':len(candidates),'resolvedCandidateCount':len(resolved),'unknownCandidateCount':len(unknown),'sampleCount':len(audits),'uniqueFetchCount':len(urls),'validationCount':len(validated),'confusion':{f'{a}__{b}':n for (a,b),n in confusion.items()},'validationAccuracy':sum(r['strictClassification']==r['coverClassification'] for r in validated)/len(validated) if validated else None,'unknownSampleCount':len(unknown_a),'unknownRecoveredCount':sum(bool(r.get('coverClassification')) for r in unknown_a),'unknownRecoveredUSCount':sum(r.get('coverClassification')=='US' for r in unknown_a),'unknownRecoveredNonUSCount':sum(r.get('coverClassification')=='NON_US' for r in unknown_a),'fetchErrorCount':sum('error' in r for r in fetched.values()),'audits':audits}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'audits','masterTransports'}},sort_keys=True),flush=True)

if __name__=='__main__': main()
