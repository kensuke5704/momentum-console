#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}

STATE_NAMES={
'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY','District of Columbia':'DC'
}
STATE_CODES=set(STATE_NAMES.values())
LABEL_RE=re.compile(r'(?:state|jurisdiction)\s+or\s+other\s+jurisdiction\s+of\s+(?:incorporation|organization)|state\s+of\s+incorporation|jurisdiction\s+of\s+incorporation\s+or\s+organization',re.I)
ARCHIVE_CIK_RE=re.compile(r'/edgar/data/(\d+)/',re.I)

class TableCells(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.rows=[]; self.row=[]; self.cell=None
    def handle_starttag(self,tag,attrs):
        t=tag.lower()
        if t=='tr': self.row=[]
        elif t in {'td','th'}: self.cell=[]
        elif t=='br' and self.cell is not None: self.cell.append(' ')
    def handle_data(self,data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self,tag):
        t=tag.lower()
        if t in {'td','th'} and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        elif t=='tr':
            if self.row: self.rows.append(self.row)
            self.row=[]

def extract_us_state(text:str):
    parser=TableCells()
    try: parser.feed(text)
    except Exception: pass
    candidates=[]
    for row in parser.rows:
        if not any(LABEL_RE.search(c or '') for c in row):
            continue
        for cell in row:
            c=' '.join(html.unescape(cell).split())
            for name,code in STATE_NAMES.items():
                if re.search(r'\b'+re.escape(name)+r'\b',c,re.I): candidates.append((code,name,'TABLE_ROW_FULL_STATE'))
            # Accept an abbreviation only if the complete cell is essentially the two-letter code.
            m=re.fullmatch(r'\s*([A-Z]{2})\s*',c)
            if m and m.group(1) in STATE_CODES: candidates.append((m.group(1),m.group(1),'TABLE_ROW_EXACT_CODE'))
    # Common layout: value and explanatory label are in the same cell, with value immediately before label.
    plain=html.unescape(re.sub(r'<[^>]+>',' ',text))
    plain=' '.join(plain.split())
    for lm in LABEL_RE.finditer(plain):
        context=plain[max(0,lm.start()-180):min(len(plain),lm.end()+80)]
        for name,code in STATE_NAMES.items():
            if re.search(r'\b'+re.escape(name)+r'\b',context,re.I): candidates.append((code,name,'LABEL_CONTEXT_FULL_STATE'))
    codes=sorted({x[0] for x in candidates})
    if len(codes)==1:
        code=codes[0]; evidence=next(x for x in candidates if x[0]==code)
        return code,evidence[1],evidence[2]
    return None,None,None

def fetch_submission(url:str,limit=900_000):
    last=None
    for candidate in (url,'https://r.jina.ai/'+url):
        try:
            headers=dict(UA)
            if candidate==url: headers['Range']=f'bytes=0-{limit-1}'
            req=urllib.request.Request(candidate,headers=headers)
            with urllib.request.urlopen(req,timeout=25) as r:
                return r.read(limit).decode('latin-1','replace'),candidate,getattr(r,'status',None)
        except Exception as e: last=e
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')

def seed_info(row):
    positives=[]
    for attempt in row.get('attempts',[]):
        if int(attempt.get('historicalExactCikCount') or 0)==1 and attempt.get('seedCik'):
            positives.append(attempt)
    ciks=sorted({str(a['seedCik']).zfill(10) for a in positives})
    if len(ciks)!=1: return None,[]
    cik=ciks[0]; filings=[]
    for a in positives:
        if str(a.get('seedCik')).zfill(10)!=cik: continue
        for f in a.get('filingAttempts',[]):
            url=f.get('submissionUrl')
            if not url or f.get('error'): continue
            if f.get('acceptanceDate') and row.get('asOfReportDate') and f['acceptanceDate']>row['asOfReportDate']: continue
            m=ARCHIVE_CIK_RE.search(url)
            if not m or str(int(m.group(1))).zfill(10)!=cik: continue
            filings.append({'form':f.get('form'),'dateFiled':f.get('dateFiled'),'acceptanceDate':f.get('acceptanceDate'),'submissionUrl':url})
    seen=set(); uniq=[]
    for f in filings:
        if f['submissionUrl'] not in seen: seen.add(f['submissionUrl']); uniq.append(f)
    return cik,uniq

def main():
    shard_i=int(os.environ.get('SHARD_INDEX','0')); shard_n=int(os.environ.get('SHARD_COUNT','1'))
    data=json.loads(SRC.read_text())
    unknown=[r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN']
    by_cik=defaultdict(list); no_seed=[]
    for row in unknown:
        cik,filings=seed_info(row)
        if not cik: no_seed.append(row); continue
        by_cik[cik].append((row,filings))
    ciks=sorted(by_cik)
    shard_ciks=[c for i,c in enumerate(ciks) if i%shard_n==shard_i]
    results=[]; recovered_queries=0; recovered_ciks=0; fetch_errors=0
    for n,cik in enumerate(shard_ciks,1):
        rows=sorted(by_cik[cik],key=lambda x:x[0].get('asOfReportDate') or '')
        # Use only filings already accepted by the strict resolver for the earliest query date.
        earliest_row,filings=rows[0]
        evidence=None; attempts=[]
        for f in filings[:3]:
            try:
                text,tr,status=fetch_submission(f['submissionUrl'])
                state,name,method=extract_us_state(text)
                attempts.append({**f,'transport':tr,'httpStatus':status,'stateCode':state,'stateName':name,'extractMethod':method})
                if state:
                    evidence={**f,'transport':tr,'stateCode':state,'stateName':name,'extractMethod':method}
                    break
            except Exception as e:
                fetch_errors+=1; attempts.append({**f,'error':type(e).__name__})
        if evidence: recovered_ciks+=1
        for row,_ in rows:
            report=row.get('asOfReportDate')
            applicable=bool(evidence and evidence.get('dateFiled') and report and evidence['dateFiled']<=report)
            rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':report,'historicalExactCik':cik,'classification':'US' if applicable else 'UNKNOWN','attempts':attempts}
            if applicable:
                rec.update({'resolutionSource':'PIT_FILING_COVER_US_JURISDICTION','stateCode':evidence['stateCode'],'stateName':evidence['stateName'],'evidenceForm':evidence.get('form'),'evidenceDateFiled':evidence.get('dateFiled'),'evidenceSubmissionUrl':evidence.get('submissionUrl'),'extractMethod':evidence.get('extractMethod')}); recovered_queries+=1
            results.append(rec)
        if n%20==0: print('PROGRESS',json.dumps({'shard':shard_i,'ciksDone':n,'recoveredCiks':recovered_ciks,'recoveredQueries':recovered_queries,'fetchErrors':fetch_errors}),flush=True)
    out={'purpose':'Return-independent PIT US-country recovery for strict UNKNOWN identities. The historical exact issuer-name -> unique CIK seed and pre-report-date submission candidates are reused from the strict resolver. A row is promoted to US only when the historical filing cover itself explicitly presents a recognized US state name (or an exact two-letter state code cell) adjacent to the SEC cover label State or other jurisdiction of incorporation or organization / state of incorporation. No current metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','shardIndex':shard_i,'shardCount':shard_n,'allInputUnknownCount':len(unknown),'allSeededCikCount':len(ciks),'shardCikCount':len(shard_ciks),'recoveredCikCount':recovered_ciks,'recoveredIdentityDateCount':recovered_queries,'fetchErrorCount':fetch_errors,'results':results}
    p=ROOT/f'data/research/country-cover-state-recovery-v29-shard-{shard_i}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__': main()
