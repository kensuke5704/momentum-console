#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-submission-header-country-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('base',ROOT/'scripts'/'research-sec-index-headers-country-pilot-2006.py')
base=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(base)
old=base.old

def flat_submission_state(target,cik,text):
    # 2005 complete submissions use a flat SEC-HEADER grammar such as:
    # COMPANY DATA / COMPANY CONFORMED NAME / CENTRAL INDEX KEY / STATE OF INCORPORATION.
    header=text.split('</SEC-HEADER>',1)[0]
    nt=base.normalize_company(target);zcik=str(cik).zfill(10)
    blocks=re.split(r'(?im)^\s*COMPANY\s+DATA\s*:\s*$',header)
    for block in blocks[1:]:
        part=re.split(r'(?im)^\s*(?:FILING\s+VALUES|BUSINESS\s+ADDRESS|MAIL\s+ADDRESS|FORMER\s+COMPANY)\s*:\s*$',block,maxsplit=1)[0]
        nm=re.search(r'(?im)^\s*COMPANY\s+CONFORMED\s+NAME\s*:\s*(.+?)\s*$',part)
        ck=re.search(r'(?im)^\s*CENTRAL\s+INDEX\s+KEY\s*:\s*(\d{1,10})\s*$',part)
        st=re.search(r'(?im)^\s*STATE\s+OF\s+INCORPORATION\s*:\s*([A-Z0-9]{2,3})\s*$',part)
        if not nm or not ck:continue
        name=nm.group(1).strip();mcik=ck.group(1).zfill(10)
        if mcik==zcik and base.normalize_company(name)==nt and st:
            return st.group(1).upper(),name
    return None,None

def resolve(row,master_rows):
    target=base.normalize_company(row.get('issuer') or '');dateb=row['asOfReportDate']
    rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
    issuer_rows=[r for r in master_rows if r['form'] in base.ISSUER_FORMS and r['dateFiled']<=dateb]
    exact=[r for r in issuer_rows if r['normalizedCompany']==target];by=defaultdict(list)
    for r in exact:by[r['cik']].append(r)
    rec['historicalExactCikCount']=len(by);rec['historicalExactCiks']=sorted(by)[:8]
    if len(by)==1:
        seed=next(iter(by));source='HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME';candidates=sorted(by[seed],key=base.filing_sort_key)
    else:
        cm=base.cur.CM.get((row.get('ticker') or '').upper(),[])
        current=[x for x in cm if base.normalize_company(x.get('title') or '')==target]
        if len(current)!=1:return rec
        seed=current[0]['cik'];source='CURRENT_TICKER_EXACT_NAME'
        candidates=sorted([r for r in issuer_rows if r['cik']==seed],key=base.filing_sort_key)
    rec['seedCik']=seed;rec['seedSource']=source;rec['filingCandidateCount']=len(candidates)
    for fr in candidates[:6]:
        try:
            text,url,status=base.submission_prefix(fr['filename'],65536)
            acceptance=re.search(r'(?im)^\s*<ACCEPTANCE-DATETIME>\s*(\d{8})',text)
            acceptance_date=(acceptance.group(1)[:4]+'-'+acceptance.group(1)[4:6]+'-'+acceptance.group(1)[6:8]) if acceptance else None
            st,name=flat_submission_state(row['issuer'],seed,text)
            rec.setdefault('attempts',[]).append({'form':fr['form'],'dateFiled':fr['dateFiled'],'submissionUrl':url,'httpStatus':status,'acceptanceDate':acceptance_date,'historicalEntityName':name,'stateCode':st})
            if acceptance_date and acceptance_date>dateb:
                continue
            if st:
                rec.update({'classification':'US' if st in old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_SUBMISSION_FLAT_HEADER_ENTITY_STATE','submissionUrl':url,'historicalEntityName':name,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'acceptanceDate':acceptance_date});return rec
        except Exception as e:
            rec.setdefault('attempts',[]).append({'form':fr['form'],'dateFiled':fr['dateFiled'],'error':type(e).__name__})
        time.sleep(.03)
    return rec

def main():
    data=json.loads(SRC.read_text())
    unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:10]
    years=sorted({int(r['asOfReportDate'][:4]) for r in unknown});master_rows,transports=base.load_master(years)
    results=[]
    for row in unknown:
        rec=resolve(row,master_rows);results.append(rec)
        print('COUNTRY',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','seedCik','seedSource','classification','stateCode','resolutionSource','evidenceForm','evidenceDateFiled']}),flush=True)
    resolved=[r for r in results if r['classification']!='UNKNOWN']
    out={'purpose':'Top-10 high-weight remaining UNKNOWN country pilot using exact historical issuer-form name -> CIK seeding from official 2005 SEC master indexes, then bounded reads of official complete-submission SEC-HEADER text. Classification requires matching historical company name, same seeded CIK and STATE OF INCORPORATION in one COMPANY DATA block; acceptance date, when present, must not exceed the legacy report date. Current ticker metadata is exact-name CIK fallback only. No current state, returns, ranks or strategy outcomes are used.','masterYears':years,'masterIndexTransports':transports,'sampleCount':len(results),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in results),'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('results','masterIndexTransports')}),flush=True)
if __name__=='__main__':main()
