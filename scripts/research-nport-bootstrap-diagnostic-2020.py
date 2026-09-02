#!/usr/bin/env python3
from __future__ import annotations
import gzip, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
OUT=ROOT/'data'/'research'/'nport-bootstrap-diagnostic-2020.json'

def month(x): return x[:7] if isinstance(x,str) and len(x)>=7 else None

def main():
    with gzip.open(SRC,'rt',encoding='utf-8') as f: p=json.load(f)
    rows=p.get('snapshots') or p.get('filings') or []
    r20=[r for r in rows if str(r.get('reportDate') or '').startswith('2020-') or str(r.get('filingDate') or '').startswith('2020-')]
    reports=Counter(month(r.get('reportDate')) for r in r20); reports.pop(None,None)
    filings=Counter(month(r.get('filingDate')) for r in r20); filings.pop(None,None)
    series={r.get('seriesId') for r in r20 if r.get('seriesId')}
    holdings=sum(len(r.get('holdings',[])) for r in r20)
    named=sum(1 for r in r20 for h in r.get('holdings',[]) if h.get('issuerName'))
    symbols=sum(1 for r in r20 for h in r.get('holdings',[]) if h.get('symbol'))
    dates_f=sorted(str(r.get('filingDate')) for r in r20 if r.get('filingDate'))
    dates_r=sorted(str(r.get('reportDate')) for r in r20 if r.get('reportDate'))
    out={'year':2020,'purpose':'Describe repository N-PORT bootstrap coverage independently of legacy-parser results.',
         'bootstrapEndQuarter':p.get('endQuarter'),'totalSnapshots':len(rows),'snapshotsTouching2020':len(r20),'uniqueSeries2020':len(series),
         'firstFilingDate':dates_f[0] if dates_f else None,'lastFilingDate':dates_f[-1] if dates_f else None,
         'firstReportDate':dates_r[0] if dates_r else None,'lastReportDate':dates_r[-1] if dates_r else None,
         'filingMonthCounts':dict(sorted(filings.items())),'reportMonthCounts':dict(sorted(reports.items())),
         'holdingRows2020':holdings,'issuerNameRows2020':named,'issuerNameRate':named/holdings if holdings else None,
         'symbolRows2020':symbols,'symbolRate':symbols/holdings if holdings else None}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps(out),flush=True)
if __name__=='__main__': main()
