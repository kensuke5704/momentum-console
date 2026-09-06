#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from collections import defaultdict, Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT=ROOT/'data/research/country-cover-jurisdiction-validation-v29.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
US_STATE_NAMES={
'ALABAMA','ALASKA','ARIZONA','ARKANSAS','CALIFORNIA','COLORADO','CONNECTICUT','DELAWARE','FLORIDA','GEORGIA','HAWAII','IDAHO','ILLINOIS','INDIANA','IOWA','KANSAS','KENTUCKY','LOUISIANA','MAINE','MARYLAND','MASSACHUSETTS','MICHIGAN','MINNESOTA','MISSISSIPPI','MISSOURI','MONTANA','NEBRASKA','NEVADA','NEW HAMPSHIRE','NEW JERSEY','NEW MEXICO','NEW YORK','NORTH CAROLINA','NORTH DAKOTA','OHIO','OKLAHOMA','OREGON','PENNSYLVANIA','RHODE ISLAND','SOUTH CAROLINA','SOUTH DAKOTA','TENNESSEE','TEXAS','UTAH','VERMONT','VIRGINIA','WASHINGTON','WEST VIRGINIA','WISCONSIN','WYOMING','DISTRICT OF COLUMBIA'}
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'}
FORM_PRIORITY={'10-K':0,'10-K/A':1,'10-Q':2,'10-Q/A':3,'8-K':4,'8-K/A':5,'S-8':6,'S-8 POS':7}
CACHE={}


def fetch_text(url,limit=1_200_000,timeout=25):
    if url in CACHE:return CACHE[url]
    last=None
    for candidate in ('https://r.jina.ai/'+url,url):
        try:
            req=urllib.request.Request(candidate,headers=UA)
            with urllib.request.urlopen(req,timeout=timeout) as r:text=r.read(limit).decode('latin-1','replace')
            CACHE[url]=(text,candidate);return CACHE[url]
        except Exception as e:last=e
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')


def load_master(years):
    rows=[];transports={}
    for year in years:
        for q in range(1,5):
            base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
            try:
                req=urllib.request.Request(base+'/master.zip',headers=UA)
                with urllib.request.urlopen(req,timeout=35) as r:data=r.read(20_000_000)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    name=next(n for n in z.namelist() if n.lower().endswith('master.idx'))
                    text=z.read(name).decode('latin-1','replace');tr=base+'/master.zip'
            except Exception:
                text,tr=fetch_text(base+'/master.idx',20_000_000,45)
            transports[f'{year}Q{q}']=tr
            for line in text.splitlines():
                p=line.split('|')
                if len(p)<5 or not p[0].strip().isdigit():continue
                cik,company,form,date,filename=[x.strip() for x in p[:5]]
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):continue
                rows.append({'cik':cik.zfill(10),'company':company,'form':form.upper(),'dateFiled':date,'filename':filename})
    return rows,transports


def seed_cik(row):
    seeds=set()
    for a in row.get('attempts',[]):
        if a.get('historicalExactCikCount')==1 and a.get('seedCik'):seeds.add(str(a['seedCik']).zfill(10))
    if len(seeds)==1:return next(iter(seeds))
    if row.get('seedSource')=='HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME' and row.get('seedCik'):return str(row['seedCik']).zfill(10)
    return None


def submission_url(filename):
    return 'https://www.sec.gov/Archives/'+filename.lstrip('/')


def clean_line(s):
    s=re.sub(r'[*_`#]+',' ',s)
    s=re.sub(r'\^\{[^}]*\}',' ',s)
    s=s.replace('|',' | ')
    return ' '.join(s.split()).strip(' -|:')


def candidate_before_label(lines,i):
    # Cover-page tables put the jurisdiction value immediately before the explanatory label.
    candidates=[]
    for j in range(i-1,max(-1,i-7),-1):
        raw=clean_line(lines[j])
        if not raw:continue
        # first table cell is normally the jurisdiction; remove obvious adjacent EIN cell.
        cell=clean_line(raw.split('|')[0])
        if not cell:continue
        if re.search(r'(?i)(state or other jurisdiction|incorporation or organization|IRS|employer identification|exact name|commission file|securities and exchange)',cell):continue
        if re.fullmatch(r'[\d\- ]{5,}',cell):continue
        candidates.append(cell)
    return candidates


def normalize_jurisdiction(s):
    s=re.sub(r'\([^)]*\)',' ',s)
    s=' '.join(s.upper().replace('.',' ').replace(',',' ').split())
    return s.strip()


def classify_jurisdiction(value):
    v=normalize_jurisdiction(value)
    if v in US_STATE_NAMES or v in US_CODES or v in {'UNITED STATES','UNITED STATES OF AMERICA','USA','U S A'}:
        return 'US'
    # Only accept a non-US value if it is a short textual jurisdiction token/phrase,
    # not an address, registrant name, form label, or numeric identifier.
    if 2 <= len(v) <= 50 and re.fullmatch(r'[A-Z][A-Z ]+',v) and not re.search(r'\b(INC|CORP|CORPORATION|COMPANY|CO|LTD|LIMITED|PLC|FORM|REPORT|COMMISSION|STREET|ROAD|AVENUE|FLOOR)\b',v):
        return 'NON_US'
    return None


def parse_cover(text):
    lines=text.replace('\r','').split('\n')
    hits=[]
    for i,line in enumerate(lines):
        if re.search(r'(?i)state\s+or\s+other\s+jurisdiction\s+of\s+incorporation|state\s+of\s+incorporation',line):
            for cand in candidate_before_label(lines,i):
                cls=classify_jurisdiction(cand)
                if cls:
                    hits.append((cand,cls,i));break
    uniq={(normalize_jurisdiction(v),c) for v,c,_ in hits}
    if len({c for _,c in uniq})==1 and uniq:
        # Preserve one representative jurisdiction string.
        val,cls=sorted(uniq)[0]
        return val,cls
    return None,None


def choose_filing(by_cik,cik,report):
    rows=[r for r in by_cik.get(cik,[]) if r['dateFiled']<=report and r['form'] in FORM_PRIORITY]
    if not rows:return None
    rows.sort(key=lambda r:(FORM_PRIORITY[r['form']],-int(r['dateFiled'].replace('-','')),r['filename']))
    return rows[0]


def main():
    data=json.loads(SRC.read_text());rows=data.get('resolutionAudit',[])
    years=sorted({int(r['asOfReportDate'][:4]) for r in rows if r.get('asOfReportDate')});years=sorted(set(years+[y-1 for y in years]))
    master,transports=load_master(years);by_cik=defaultdict(list)
    for r in master:by_cik[r['cik']].append(r)

    candidates=[]
    for row in rows:
        cik=seed_cik(row);report=row.get('asOfReportDate')
        if not cik or not report:continue
        filing=choose_filing(by_cik,cik,report)
        if filing:candidates.append((row,cik,filing))

    # Validate on a deterministic, outcome-independent sample of already-resolved rows,
    # plus a deterministic UNKNOWN sample to estimate recoverable coverage.
    resolved=[x for x in candidates if x[0].get('classification') in {'US','NON_US'}]
    unknown=[x for x in candidates if x[0].get('classification')=='UNKNOWN']
    resolved.sort(key=lambda x:(x[0].get('ticker') or '',x[0].get('securityId') or '',x[0].get('asOfReportDate') or ''))
    unknown.sort(key=lambda x:(x[0].get('ticker') or '',x[0].get('securityId') or '',x[0].get('asOfReportDate') or ''))
    def quantile_sample(arr,n):
        if not arr:return []
        n=min(n,len(arr));pos=sorted(set(min(len(arr)-1,(i*len(arr))//n) for i in range(n)));return [arr[i] for i in pos]
    sample=quantile_sample(resolved,240)+quantile_sample(unknown,240)

    audits=[]
    for row,cik,filing in sample:
        rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'seedCik':cik,'strictClassification':row.get('classification'),'form':filing['form'],'dateFiled':filing['dateFiled'],'filename':filing['filename']}
        try:
            text,tr=fetch_text(submission_url(filing['filename']))
            value,cls=parse_cover(text)
            rec.update({'transport':tr,'jurisdiction':value,'coverClassification':cls})
        except Exception as e:rec['error']=type(e).__name__
        audits.append(rec)

    validated=[r for r in audits if r.get('strictClassification') in {'US','NON_US'} and r.get('coverClassification')]
    confusion=Counter((r['strictClassification'],r['coverClassification']) for r in validated)
    unknown_a=[r for r in audits if r.get('strictClassification')=='UNKNOWN']
    out={'purpose':'Return-independent validation of explicit jurisdiction-of-incorporation text on pre-report-date SEC filing cover pages. Historical issuer identity is already bound to one CIK. The parser uses only the filing cover phrase and immediately adjacent jurisdiction value. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','masterYears':years,'masterTransports':transports,'candidateCount':len(candidates),'resolvedCandidateCount':len(resolved),'unknownCandidateCount':len(unknown),'sampleCount':len(audits),'validationCount':len(validated),'confusion':{f'{a}__{b}':n for (a,b),n in confusion.items()},'validationAccuracy':sum(a==b for a,b in [(r['strictClassification'],r['coverClassification']) for r in validated])/len(validated) if validated else None,'unknownSampleCount':len(unknown_a),'unknownRecoveredCount':sum(bool(r.get('coverClassification')) for r in unknown_a),'unknownRecoveredUSCount':sum(r.get('coverClassification')=='US' for r in unknown_a),'unknownRecoveredNonUSCount':sum(r.get('coverClassification')=='NON_US' for r in unknown_a),'fetchCacheCount':len(CACHE),'audits':audits}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'audits','masterTransports'}},sort_keys=True),flush=True)

if __name__=='__main__':main()
