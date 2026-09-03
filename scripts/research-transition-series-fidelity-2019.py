#!/usr/bin/env python3
from __future__ import annotations
import gzip, importlib.util, json, re, statistics, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-series-fidelity-2019.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'

sspec=importlib.util.spec_from_file_location('seg',ROOT/'scripts'/'research-nq-series-segmentation-2006.py')
seg=importlib.util.module_from_spec(sspec); sspec.loader.exec_module(seg)

# Fixed before seeing overlap results. Latest available N-Q candidates from five transition registrants.
SOURCES=[
 ('0001329377','First Trust Exchange-Traded Fund',['0001445546-18-005192']),
 ('0001364608','First Trust Exchange-Traded Fund II',['0001445546-19-001205']),
 ('0001552740','First Trust Exchange-Traded Fund VI',['0001445546-19-001208','0001445546-19-001184']),
 ('0001467831','ETF Managers Trust',['0000894189-19-005882']),
 ('0001408970','AdvisorShares Trust',['0001615774-18-012797']),
]
REPORT_DATE=re.compile(r'(?im)^\s*CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$')

def iso8(x): return f'{x[:4]}-{x[4:6]}-{x[6:8]}' if x and len(x)==8 else None

def sec_submission(cik,acc):
    compact=acc.replace('-','')
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}.txt'

def norm(s):
    s=(s or '').upper().replace('&',' AND ')
    for a,b in [('INCORPORATED','INC'),('CORPORATION','CORP'),('COMPANY','CO'),('LIMITED','LTD')]: s=re.sub(rf'\b{a}\b',b,s)
    s=re.sub(r'\bTHE\b',' ',s)
    return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())

def nq_holdings(block):
    _,_,_,parsed=seg.nqpilot.parse_holdings(block)
    out=[]
    for h in parsed:
        v=max(0.0,float(h.get('marketValue') or 0)); d=' '.join(str(h.get('description') or '').split())
        if v>0 and d: out.append((norm(d),v,d))
    total=sum(v for _,v,_ in out)
    return [{'name':n,'raw':d,'weight':100*v/total} for n,v,d in out] if total else []

def earliest_nport_by_series(filings):
    d={}
    for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
        sid=f.get('seriesId')
        if sid and sid not in d: d[sid]=f
    return d

def main():
    with gzip.open(BOOT,'rt',encoding='utf-8') as fh: boot=json.load(fh)
    filings=boot.get('snapshots',boot) if isinstance(boot,dict) else boot
    first=earliest_nport_by_series(filings)
    rows=[]; fetches=[]
    for cik,label,accs in SOURCES:
        for acc in accs:
            try:
                _,submission=seg.meta.fetch_prefix(sec_submission(cik,acc))
                rm=REPORT_DATE.search(submission); report=iso8(rm.group(1) if rm else None)
                series=[s for s in seg.meta.parse_series_contracts(submission,label) if s.get('seriesId')]
                _,text=seg.embedded_primary_nq(submission)
                grouped,audit=seg.grouped_schedule_blocks(text,series)
                by={s['seriesId']:s for s in series}
                matched=0
                for sid,blocks in grouped.items():
                    nf=first.get(sid)
                    if not nf: continue
                    nh=nq_holdings('\n'.join(blocks))
                    ph=[{'name':norm(h.get('issuerName') or ''),'symbol':h.get('symbol'),'weight':float(h.get('weight') or 0)} for h in nf.get('holdings',[]) if h.get('issuerName')]
                    pnames={x['name'] for x in ph if x['name']}
                    common=[h for h in nh if h['name'] in pnames]
                    nq_count=len(nh); nport_count=len(ph)
                    overlap=len(common)/nq_count if nq_count else None
                    w=sum(h['weight'] for h in common)/100 if nq_count else None
                    gap=None
                    if report and nf.get('reportDate'):
                        from datetime import date
                        gap=(date.fromisoformat(nf['reportDate'])-date.fromisoformat(report)).days
                    row={'cik':cik,'registrant':label,'nqAccession':acc,'seriesId':sid,'seriesName':by.get(sid,{}).get('seriesName'),'nqReportDate':report,'nportReportDate':nf.get('reportDate'),'daysBetweenReports':gap,'nqHoldings':nq_count,'nportHoldings':nport_count,'issuerCountOverlapRate':overlap,'nqWeightOverlapRate':w}
                    rows.append(row); matched+=1
                    print('PAIR',json.dumps(row),flush=True)
                fetches.append({'cik':cik,'accession':acc,'reportDate':report,'seriesMetadata':len(series),'groupedSeries':len(grouped),'sameSeriesPairs':matched,'assignedMarkers':sum(bool(x.get('seriesId')) for x in audit)})
            except Exception as e:
                fetches.append({'cik':cik,'accession':acc,'error':repr(e)}); print('FAIL',cik,acc,repr(e),flush=True)
            time.sleep(.25)
    valid=[r for r in rows if r['issuerCountOverlapRate'] is not None]
    summary={'purpose':'Gate B precursor: actual legacy N-Q same-series holdings fidelity against earliest N-PORT. No return/performance information used.','fixedSourceRule':'Latest available N-Q accession(s) from five registrants fixed from transition discovery before overlap calculation.','filingsAttempted':sum(len(x[2]) for x in SOURCES),'filingsSucceeded':sum('error' not in x for x in fetches),'sameSeriesPairs':len(valid),'medianIssuerCountOverlapRate':statistics.median([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'minimumIssuerCountOverlapRate':min([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'medianNqWeightOverlapRate':statistics.median([r['nqWeightOverlapRate'] for r in valid]) if valid else None,'pairs':rows,'fetches':fetches}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ('pairs','fetches')}),flush=True)
if __name__=='__main__': main()
