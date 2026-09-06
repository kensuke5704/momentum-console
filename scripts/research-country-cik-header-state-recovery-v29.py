#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}


def seed_info(row):
    ciks=set(); filings={}
    for a in row.get('attempts',[]):
        if int(a.get('historicalExactCikCount') or 0)!=1 or not a.get('seedCik'):
            continue
        cik=str(a['seedCik']).zfill(10); ciks.add(cik)
        for f in a.get('filingAttempts',[]):
            url=f.get('submissionUrl')
            if not url: continue
            if f.get('acceptanceDate') and row.get('asOfReportDate') and f['acceptanceDate']>row['asOfReportDate']: continue
            filings[url]={'form':f.get('form'),'dateFiled':f.get('dateFiled'),'acceptanceDate':f.get('acceptanceDate'),'submissionUrl':url}
    if len(ciks)!=1: return None,[]
    cik=next(iter(ciks))
    # Require the accession path itself to be under the exact seeded CIK.
    good=[]
    for f in filings.values():
        m=re.search(r'/Archives/edgar/data/(\d+)/',f['submissionUrl'],re.I)
        if m and str(int(m.group(1))).zfill(10)==cik:
            good.append(f)
    good.sort(key=lambda x:((x.get('dateFiled') or ''),(x.get('form') or '')),reverse=True)
    return cik,good


def fetch_prefix(url,limit=180_000):
    last=None
    for candidate in (url,'https://r.jina.ai/'+url):
        try:
            headers=dict(UA)
            if candidate==url: headers['Range']=f'bytes=0-{limit-1}'
            req=urllib.request.Request(candidate,headers=headers)
            with urllib.request.urlopen(req,timeout=20) as r:
                return r.read(limit).decode('latin-1','replace'),candidate,getattr(r,'status',None)
        except Exception as e: last=e
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')


def states_for_cik(text,cik):
    zcik=str(cik).zfill(10); states=[]
    # Flat SEC-HEADER grammar.
    header=text.split('</SEC-HEADER>',1)[0]
    blocks=re.split(r'(?im)^\s*COMPANY\s+DATA\s*:\s*$',header)
    for block in blocks[1:]:
        part=re.split(r'(?im)^\s*(?:FILING\s+VALUES|BUSINESS\s+ADDRESS|MAIL\s+ADDRESS|FORMER\s+COMPANY)\s*:\s*$',block,maxsplit=1)[0]
        ck=re.search(r'(?im)^\s*CENTRAL\s+INDEX\s+KEY\s*:\s*(\d{1,10})\s*$',part)
        st=re.search(r'(?im)^\s*STATE\s+OF\s+INCORPORATION\s*:\s*([A-Z0-9]{2,3})\s*$',part)
        if ck and st and ck.group(1).zfill(10)==zcik: states.append(st.group(1).upper())
    # Older SGML grammar.
    for block in re.findall(r'<COMPANY-DATA>(.*?)(?=</COMPANY-DATA>|<FILING-VALUES>|<BUSINESS-ADDRESS>|<MAIL-ADDRESS>|<FORMER-COMPANY>|</FILER>|</ISSUER>|$)',text,re.I|re.S):
        ck=re.search(r'<CIK>\s*(\d{1,10})',block,re.I); st=re.search(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})',block,re.I)
        if ck and st and ck.group(1).zfill(10)==zcik: states.append(st.group(1).upper())
    return sorted(set(states))


def main():
    shard_i=int(os.environ.get('SHARD_INDEX','0')); shard_n=int(os.environ.get('SHARD_COUNT','1'))
    data=json.loads(SRC.read_text()); unknown=[r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN']
    rows=[]
    for row in unknown:
        cik,filings=seed_info(row); rows.append((row,cik,filings))
    seeded=[x for x in rows if x[1]]
    seeded.sort(key=lambda x:(x[1],x[0].get('asOfReportDate') or '',x[0].get('ticker') or ''))
    shard=[x for i,x in enumerate(seeded) if i%shard_n==shard_i]
    cache={}; results=[]; resolved=us=nonus=conflicts=errors=0
    for i,(row,cik,filings) in enumerate(shard,1):
        rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'historicalExactCik':cik,'classification':'UNKNOWN','attempts':[]}
        positives=[]
        for f in filings[:6]:
            url=f['submissionUrl']
            try:
                if url not in cache: cache[url]=fetch_prefix(url)
                text,tr,status=cache[url]; states=states_for_cik(text,cik)
                rec['attempts'].append({**f,'transport':tr,'httpStatus':status,'stateCodes':states})
                for state in states: positives.append((state,f,tr))
            except Exception as e:
                errors+=1; rec['attempts'].append({**f,'error':type(e).__name__})
        classes=sorted({'US' if s in US_CODES else 'NON_US' for s,_,_ in positives})
        states=sorted({s for s,_,_ in positives})
        if len(classes)>1:
            conflicts+=1; rec['countryConflictClasses']=classes; rec['countryConflictStates']=states
        elif len(classes)==1:
            cls=classes[0]; state=states[0] if len(states)==1 else None
            # Multiple state codes are allowed only if they agree on US-vs-NON_US classification.
            ev=next(x for x in positives if ('US' if x[0] in US_CODES else 'NON_US')==cls)
            rec.update({'classification':cls,'resolutionSource':'PIT_HISTORICAL_EXACT_NAME_UNIQUE_CIK_HEADER_STATE','stateCode':state,'observedStateCodes':states,'evidenceForm':ev[1].get('form'),'evidenceDateFiled':ev[1].get('dateFiled'),'evidenceSubmissionUrl':ev[1].get('submissionUrl'),'evidenceTransport':ev[2]})
            resolved+=1; us+=cls=='US'; nonus+=cls=='NON_US'
        results.append(rec)
        if i%100==0: print('PROGRESS',json.dumps({'shard':shard_i,'done':i,'resolved':resolved,'us':us,'nonus':nonus,'conflicts':conflicts,'errors':errors,'cache':len(cache)}),flush=True)
    out={'purpose':'Return-independent PIT recovery for strict-country UNKNOWN identities. Historical cleaned exact issuer name must already have resolved to exactly one CIK in the pre-report-date SEC master index. Country is then read from STATE OF INCORPORATION in a pre-report-date complete-submission header block bound to that exact CIK. The second-stage header entity name is intentionally not re-matched because CIK is the SEC unique registrant identifier; conflicting US/NON_US states are never auto-assigned. No current metadata, fuzzy matching, defaults, ranks, returns or strategy outcomes are used.','shardIndex':shard_i,'shardCount':shard_n,'allInputUnknownCount':len(unknown),'allSeededIdentityDateCount':len(seeded),'shardInputCount':len(shard),'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'conflictCount':conflicts,'fetchErrorCount':errors,'results':results}
    p=ROOT/f'data/research/country-cik-header-state-recovery-v29-shard-{shard_i}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__': main()
