#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import html
import io
import json
import os
import re
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
FORMS={'10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','DEF 14A','DEFA14A','PRE 14A','11-K','S-8','S-8 POS','20-F','20-F/A','40-F','40-F/A','6-K','6-K/A'}
FORM_PRIORITY={'10-K':0,'10-K/A':1,'10-Q':2,'10-Q/A':3,'8-K':4,'8-K/A':5,'DEF 14A':6,'DEFA14A':7,'PRE 14A':8,'20-F':9,'20-F/A':10,'40-F':11,'40-F/A':12,'6-K':13,'6-K/A':14,'11-K':15,'S-8':16,'S-8 POS':17}
LOOKBACK_DAYS=730
JURIS_RE=re.compile(r'\s*/[A-Z0-9]{2,3}/?\s*$',re.I)

def clean_issuer(s):
    s=re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$','',s or '',flags=re.I)
    return ' '.join(s.replace('’',"'").split()).strip(' .,-')

def normalize_company(s):
    s=JURIS_RE.sub('',s or '');s=clean_issuer(s).upper().replace('&',' AND ')
    s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b',' ',s)
    s=re.sub(r'[^A-Z0-9]+',' ',s);return ' '.join(s.split())

def cleaned_forms(raw):
    vals=[raw];s=raw
    pats=[r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',r'\s*/[A-Z]{2}\s*$']
    changed=True
    while changed:
        changed=False
        for p in pats:
            ns=re.sub(p,'',s,flags=re.I).strip()
            if ns!=s:vals.append(ns);s=ns;changed=True
    return list(dict.fromkeys(v for v in vals if v))

def get_master(year,q):
    base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
    try:
        req=urllib.request.Request(base+'/master.zip',headers=UA)
        with urllib.request.urlopen(req,timeout=35) as r:data=r.read(20_000_000)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name=next(n for n in z.namelist() if n.lower().endswith('master.idx'))
            return z.read(name).decode('latin-1','replace'),base+'/master.zip'
    except Exception:
        url='https://r.jina.ai/'+base+'/master.idx';req=urllib.request.Request(url,headers=UA)
        with urllib.request.urlopen(req,timeout=45) as r:return r.read(20_000_000).decode('latin-1','replace'),url

def load_master(years):
    rows=[];transports={}
    for year in years:
        for q in range(1,5):
            text,tr=get_master(year,q);transports[f'{year}Q{q}']=tr
            for line in text.splitlines():
                p=line.split('|')
                if len(p)<5 or not p[0].strip().isdigit():continue
                cik,company,form,date,filename=[x.strip() for x in p[:5]];form=form.upper()
                if form not in FORMS or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):continue
                rows.append({'cik':cik.zfill(10),'company':company,'normalizedCompany':normalize_company(company),'form':form,'dateFiled':date,'filename':filename})
    return rows,transports

def fetch_prefix(filename,limit=180_000):
    url='https://www.sec.gov/Archives/'+filename.lstrip('/');last=None
    for candidate in (url,'https://r.jina.ai/'+url):
        try:
            headers=dict(UA)
            if candidate==url:headers['Range']=f'bytes=0-{limit-1}'
            req=urllib.request.Request(candidate,headers=headers)
            with urllib.request.urlopen(req,timeout=20) as r:return r.read(limit).decode('latin-1','replace'),candidate,getattr(r,'status',None)
        except Exception as e:last=e
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')

def states_for_cik(text,cik):
    z=str(cik).zfill(10);out=[];header=text.split('</SEC-HEADER>',1)[0]
    blocks=re.split(r'(?im)^\s*COMPANY\s+DATA\s*:\s*$',header)
    for block in blocks[1:]:
        part=re.split(r'(?im)^\s*(?:FILING\s+VALUES|BUSINESS\s+ADDRESS|MAIL\s+ADDRESS|FORMER\s+COMPANY)\s*:\s*$',block,maxsplit=1)[0]
        ck=re.search(r'(?im)^\s*CENTRAL\s+INDEX\s+KEY\s*:\s*(\d{1,10})\s*$',part);st=re.search(r'(?im)^\s*STATE\s+OF\s+INCORPORATION\s*:\s*([A-Z0-9]{2,3})\s*$',part)
        if ck and st and ck.group(1).zfill(10)==z:out.append(st.group(1).upper())
    for block in re.findall(r'<COMPANY-DATA>(.*?)(?=</COMPANY-DATA>|<FILING-VALUES>|<BUSINESS-ADDRESS>|<MAIL-ADDRESS>|<FORMER-COMPANY>|</FILER>|</ISSUER>|$)',text,re.I|re.S):
        ck=re.search(r'<CIK>\s*(\d{1,10})',block,re.I);st=re.search(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})',block,re.I)
        if ck and st and ck.group(1).zfill(10)==z:out.append(st.group(1).upper())
    return sorted(set(out))

def main():
    shard_i=int(os.environ.get('SHARD_INDEX','0'));shard_n=int(os.environ.get('SHARD_COUNT','1'))
    data=json.loads(SRC.read_text());unknown=[r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN']
    report_years=[int(r['asOfReportDate'][:4]) for r in unknown if r.get('asOfReportDate')]
    years=list(range(min(report_years)-2,max(report_years)+1));master,transports=load_master(years)
    by_name=defaultdict(list)
    for r in master:by_name[r['normalizedCompany']].append(r)
    queries=[]
    for row in unknown:
        report=row.get('asOfReportDate');rd=dt.date.fromisoformat(report);floor=rd-dt.timedelta(days=LOOKBACK_DAYS)
        forms=[]
        for issuer in row.get('issuerVariants',[]):
            for f in cleaned_forms(str(issuer)):
                if f and f not in forms:forms.append(f)
        exact=[]
        for f in forms:
            for r in by_name.get(normalize_company(f),[]):
                fd=dt.date.fromisoformat(r['dateFiled'])
                if floor<=fd<=rd:exact.append(r)
        by_cik=defaultdict(list)
        for r in exact:by_cik[r['cik']].append(r)
        queries.append((row,by_cik))
    shard=[x for i,x in enumerate(queries) if i%shard_n==shard_i]
    cache={};results=[];resolved=us=nonus=ambiguous_cik=conflicts=errors=0
    for i,(row,by_cik) in enumerate(shard,1):
        rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'classification':'UNKNOWN','lookbackDays':LOOKBACK_DAYS,'historicalExactCikCount':len(by_cik),'historicalExactCiks':sorted(by_cik)[:8],'attempts':[]}
        if len(by_cik)>1:ambiguous_cik+=1
        if len(by_cik)==1:
            cik=next(iter(by_cik));rec['seedCik']=cik
            candidates=sorted(by_cik[cik],key=lambda r:(FORM_PRIORITY.get(r['form'],99),-int(r['dateFiled'].replace('-','')),r['filename']))
            seen=set();positives=[]
            for f in candidates:
                if f['filename'] in seen:continue
                seen.add(f['filename'])
                if len(seen)>6:break
                try:
                    if f['filename'] not in cache:cache[f['filename']]=fetch_prefix(f['filename'])
                    text,tr,status=cache[f['filename']];states=states_for_cik(text,cik);rec['attempts'].append({'form':f['form'],'dateFiled':f['dateFiled'],'filename':f['filename'],'transport':tr,'httpStatus':status,'stateCodes':states})
                    for s in states:positives.append((s,f,tr))
                except Exception as e:
                    errors+=1;rec['attempts'].append({'form':f['form'],'dateFiled':f['dateFiled'],'filename':f['filename'],'error':type(e).__name__})
            classes=sorted({'US' if s in US_CODES else 'NON_US' for s,_,_ in positives})
            states=sorted({s for s,_,_ in positives})
            if len(classes)>1:conflicts+=1;rec['countryConflictClasses']=classes;rec['countryConflictStates']=states
            elif len(classes)==1:
                cls=classes[0];ev=next(x for x in positives if ('US' if x[0] in US_CODES else 'NON_US')==cls);rec.update({'classification':cls,'resolutionSource':'PIT_SEC_24M_EXACT_NAME_UNIQUE_CIK_HEADER_STATE','stateCode':states[0] if len(states)==1 else None,'observedStateCodes':states,'evidenceForm':ev[1]['form'],'evidenceDateFiled':ev[1]['dateFiled'],'evidenceFilename':ev[1]['filename'],'evidenceTransport':ev[2]});resolved+=1;us+=cls=='US';nonus+=cls=='NON_US'
        results.append(rec)
        if i%50==0:print('PROGRESS',json.dumps({'shard':shard_i,'done':i,'resolved':resolved,'us':us,'nonus':nonus,'ambiguousCik':ambiguous_cik,'conflicts':conflicts,'errors':errors,'cache':len(cache)}),flush=True)
    out={'purpose':'Return-independent PIT country recovery using a fixed 730-day historical SEC lookback. For each strict UNKNOWN identity/report-date, cleaned issuer forms are exact-matched against SEC master-index issuer names only within [reportDate-730d, reportDate]. Exactly one CIK is required. Country then comes only from STATE OF INCORPORATION in a pre-report-date complete-submission header bound to that CIK; conflicting classifications are excluded. The 730-day window is a structural reporting-coverage rule chosen independently of ranks/returns and prevents the prior calendar-year omission affecting early-year snapshots. No current metadata, fuzzy matching, country default, ranks, returns or strategy outcomes are used.','lookbackDays':LOOKBACK_DAYS,'masterYears':years,'masterIndexTransports':transports,'shardIndex':shard_i,'shardCount':shard_n,'allInputUnknownCount':len(unknown),'shardInputCount':len(shard),'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'ambiguousCikCount':ambiguous_cik,'conflictCount':conflicts,'fetchErrorCount':errors,'results':results}
    p=ROOT/f'data/research/country-24m-lookback-recovery-v29-shard-{shard_i}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)
if __name__=='__main__':main()
