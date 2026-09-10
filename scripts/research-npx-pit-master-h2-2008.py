#!/usr/bin/env python3
"""Mechanical H2-2008 continuation of the frozen H1 N-PX PIT master."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import socket
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
BASE=DATA/'npx-pit-master-h1-2008-2008-06.json'
AUDIT=DATA/'npx-pit-master-h2-2008-audit.json'
SIGNALS=[('2008-07','2008-07-31'),('2008-08','2008-08-29'),('2008-09','2008-09-30'),('2008-10','2008-10-31'),('2008-11','2008-11-28'),('2008-12','2008-12-31')]
SAMPLE_COUNT=64
BROAD_CIKS={'35348','826473','68138','745463','752737','81247','916403','814232','1039949','202385','1026708'}
INDEX_BASE='https://www.sec.gov/Archives/edgar/full-index/2008/QTR{q}/master.zip'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'application/zip,text/plain,text/html,*/*','Accept-Encoding':'identity'}
BACKOFF=(3,6,12,24,36,48); MIN_INTERVAL=1.15; last_request=0.0

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
PARSER=load('frozen_npx_parser',ROOT/'scripts/research-npx-security-master-2006.py')
BUILDER=load('frozen_npx_builder',ROOT/'scripts/research-npx-security-master-build-2006.py')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for x in iter(lambda:f.read(1024*1024),b''): h.update(x)
    return h.hexdigest()

def fetch(url,limit):
    global last_request
    err=None
    for attempt in range(1,len(BACKOFF)+2):
        wait=MIN_INTERVAL-(time.monotonic()-last_request)
        if wait>0: time.sleep(wait)
        last_request=time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=90) as r: return r.read(limit)
        except urllib.error.HTTPError as x:
            err=x
            if x.code!=429 and not 500<=x.code<=599: break
        except (urllib.error.URLError,TimeoutError,socket.timeout,ConnectionError,OSError) as x: err=x
        if attempt<=len(BACKOFF): time.sleep(BACKOFF[attempt-1])
    raise RuntimeError(f'SEC transport exhausted for {url}') from err

def key(x): return (x['cik'],x['form'],x['dateFiled'],x['filename'])
def record_key(x): return (x.get('normalizedIssuer') or '',x.get('ticker'),x.get('securityId'))
def sec_url(name): return 'https://www.sec.gov/Archives/'+name.lstrip('/')

def inventory():
    hits=[]; sources=[]
    for q in (1,2,3,4):
        url=INDEX_BASE.format(q=q); raw=fetch(url,25_000_000)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            member=next((n for n in z.namelist() if n.lower().endswith('master.idx')),None)
            if not member: raise RuntimeError(f'master.idx missing from {url}')
            text=z.read(member).decode('latin-1','replace')
        sources.append({'quarter':q,'transport':url})
        for line in text.splitlines():
            p=line.split('|')
            if len(p)<5: continue
            cik,company,form,date,name=[v.strip() for v in p[:5]]; form=form.upper()
            if form in {'N-PX','N-PX/A'} and date.startswith('2008'): hits.append({'cik':cik,'company':company,'form':form,'dateFiled':date,'filename':name})
    return sorted({key(x):x for x in hits}.values(),key=lambda x:(x['dateFiled'],int(x['cik']),x['filename'])),sources

def main():
    base=json.loads(BASE.read_text())
    if base.get('signalMonth')!='2008-06' or base.get('asOf')!='2008-06-30': raise RuntimeError('unexpected H1-2008 base boundary')
    base_records=list(base['records']); base_keys=[record_key(x) for x in base_records]
    if len(base_keys)!=len(set(base_keys)): raise RuntimeError('validated base contains duplicate identity keys')
    filings,index_sources=inventory(); primary=[x for x in filings if x['form']=='N-PX']; amendments=[x for x in filings if x['form']=='N-PX/A']
    admitted={}; selections={}
    for month,asof in SIGNALS:
        reps={}
        for x in sorted((x for x in primary if x['dateFiled']<=asof),key=lambda x:(x['dateFiled'],int(x['cik']),x['filename'])): reps.setdefault(x['cik'],x)
        reps=sorted(reps.values(),key=lambda x:(int(x['cik']),x['dateFiled'],x['filename']))
        sample=reps if len(reps)<=SAMPLE_COUNT else [reps[round(i*(len(reps)-1)/(SAMPLE_COUNT-1))] for i in range(SAMPLE_COUNT)]
        broad=[x for x in reps if x['cik'] in BROAD_CIKS]; selected={key(x):x for x in sample+broad}; added=[]
        for k,x in sorted(selected.items(),key=lambda kv:(kv[1]['dateFiled'],int(kv[1]['cik']),kv[1]['filename'])):
            if k not in admitted: admitted[k]={**x,'admittedAtSignal':asof}; added.append(k)
        selections[month]={'signalMonth':month,'asOf':asof,'publicPrimaryFilings':sum(x['dateFiled']<=asof for x in primary),'publicRepresentativeCiks':len(reps),'quantileSelectedSources':len(sample),'broadSelectedSources':len(broad),'selectedUniqueSources':len(selected),'newAdmissions':len(added),'cumulativeAdmissions':len(admitted)}
    parsed={}; results=[]; errors=[]
    for source in sorted(admitted.values(),key=lambda x:(x['dateFiled'],int(x['cik']),x['filename'])):
        try:
            text=fetch(sec_url(source['filename']),20_000_000).decode('latin-1','replace'); rows=[]
            for rec in PARSER.parse_records(text): rows.append({'issuer':rec['issuer'],'normalizedIssuer':BUILDER.normalize_issuer(rec['issuer']),'ticker':rec.get('ticker'),'securityId':rec.get('securityId'),'meetingDateRaw':rec.get('meetingDateRaw'),'sourceFilingDate':source['dateFiled'],'sourceCik':source['cik'],'sourceCompany':source['company'],'sourceFilename':source['filename'],'admittedAtSignal':source['admittedAtSignal'],'sourceForm':source['form']})
            parsed[key(source)]=rows; results.append({**source,'fetchOk':True,'records':len(rows),'pairedRecords':sum(bool(x.get('ticker') and x.get('securityId')) for x in rows)})
        except Exception as x: errors.append({**source,'error':repr(x)}); results.append({**source,'fetchOk':False,'error':repr(x)})
    violations=[]; monthly=[]; prior=set()
    if errors: violations.append({'type':'FETCH_ERRORS','count':len(errors)})
    for month,asof in SIGNALS:
        active={k:x for k,x in admitted.items() if x['admittedAtSignal']<=asof and x['dateFiled']<=asof}
        if not prior.issubset(active): violations.append({'signalMonth':month,'type':'NON_MONOTONE_SOURCE_SET'})
        prior=set(active); records=list(base_records); seen=set(base_keys); candidates=added=0; dates=[]
        for k,source in sorted(active.items(),key=lambda kv:(kv[1]['dateFiled'],int(kv[1]['cik']),kv[1]['filename'])):
            if source['form']!='N-PX': violations.append({'signalMonth':month,'type':'NON_PRIMARY_ADMISSION','source':source})
            for row in parsed.get(k,[]):
                candidates+=1
                if row['sourceFilingDate']>asof or row['admittedAtSignal']>asof: violations.append({'signalMonth':month,'type':'LOOKAHEAD_RECORD','record':row}); continue
                dates.append(row['sourceFilingDate']); rkey=record_key(row)
                if rkey not in seen: seen.add(rkey); records.append(row); added+=1
        if records[:len(base_records)]!=base_records: violations.append({'signalMonth':month,'type':'BASE_MUTATED'})
        path=DATA/f'npx-pit-master-h2-2008-{month}.json'
        out={'year':2008,'signalMonth':month,'asOf':asof,'purpose':'H2 2008 PIT N-PX identity master: immutable validated 2008-06 master plus only 2008 evidence public/admitted by signal date.','baseRunId':34320224950,'baseArtifactId':10091573844,'baseSha256':sha(BASE),'baseRecordCount':len(base_records),'activeIncrementalSourceCount':len(active),'incrementalParsedRecordCandidates':candidates,'incrementalUniqueRecordsAdded':added,'pairedRecords':sum(bool(x.get('ticker') and x.get('securityId')) for x in records),'uniqueRecords':len(records),'records':records,'incrementalSources':[active[k] for k in sorted(active)]}
        path.write_text(json.dumps(out,indent=2)+'\n'); monthly.append({**selections[month],'activeIncrementalSources':len(active),'incrementalParsedRecordCandidates':candidates,'incrementalUniqueRecordsAdded':added,'totalMasterRecords':len(records),'pairedRecords':out['pairedRecords'],'maxIncrementalSourceFilingDate':max(dates) if dates else None,'output':str(path.relative_to(ROOT))})
    audit={'status':'PASS' if not violations else 'FAIL','purpose':'Pre-mapping PIT validation for H2 2008 N-PX identity masters; no N-Q mapping coverage, country, Universe, return, or strategy outcome used.','definition':'docs/research/h2-2008-npx-pit-master-validation-definition.md','baseRunId':34320224950,'baseArtifactId':10091573844,'baseSha256':sha(BASE),'baseRecordCount':len(base_records),'indexSources':index_sources,'inventory':{'allNpxAndAmendments':len(filings),'primaryNpx':len(primary),'npxAmendments':len(amendments),'uniquePrimaryCiks':len({x['cik'] for x in primary}),'filingMonthCounts':dict(sorted(Counter(x['dateFiled'][:7] for x in filings).items()))},'broadCiks':sorted(BROAD_CIKS,key=int),'sampleCount':SAMPLE_COUNT,'admittedSourceCount':len(admitted),'fetchErrorCount':len(errors),'fetchErrors':errors,'sourceResults':results,'monthly':monthly,'violations':violations}
    AUDIT.write_text(json.dumps(audit,indent=2)+'\n')
    if violations: raise SystemExit(2)
if __name__=='__main__': main()
