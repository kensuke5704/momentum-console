#!/usr/bin/env python3
from __future__ import annotations
import gzip, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/'data'/'universe-history.json'
BOOT=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'

hist=json.loads(HIST.read_text())
if isinstance(hist,list):
    records=hist
elif isinstance(hist,dict):
    print('HIST_KEYS',json.dumps(sorted(hist.keys())),flush=True)
    candidates=[]
    for k,v in hist.items():
        if isinstance(v,list):
            candidates.extend(v)
        elif isinstance(v,dict):
            if isinstance(v.get('records'),list): candidates.extend(v['records'])
            if isinstance(v.get('months'),list): candidates.extend(v['months'])
    records=candidates
else:
    records=[]
print('HIST_DIAG',json.dumps({'topType':type(hist).__name__,'candidateRecords':len(records),'sampleKeys':sorted(records[0].keys()) if records and isinstance(records[0],dict) else []}),flush=True)
jan=next((r for r in records if isinstance(r,dict) and (r.get('signalMonth')=='2020-01' or r.get('month')=='2020-01')),None)
if not jan:
    print('MONTH_SAMPLES',json.dumps([r.get('signalMonth',r.get('month')) for r in records[:20] if isinstance(r,dict)]),flush=True)
    raise RuntimeError('2020-01 not found')
with gzip.open(BOOT,'rt',encoding='utf-8') as f: boot=json.load(f)
filings=boot if isinstance(boot,list) else boot.get('filings',boot.get('records',[]))
by_acc={f.get('accession'):f for f in filings if isinstance(f,dict)}
rows=[]
for s in jan.get('sourceFilings',[]):
    b=by_acc.get(s.get('accession'),{})
    rows.append({'accession':s.get('accession'),'seriesId':s.get('seriesId'),'seriesName':s.get('seriesName'),'filingDate':s.get('filingDate'),'reportDate':b.get('reportDate'),'holdingCount':len(b.get('holdings',[])) if isinstance(b.get('holdings'),list) else None})
print('SUMMARY',json.dumps({'signalMonth':'2020-01','asOf':jan.get('asOf'),'universeSize':len(jan.get('symbols',[])),'sourceSeriesCount':len(rows),'uniqueSeries':len({r['seriesId'] for r in rows})}),flush=True)
for r in rows: print('SERIES',json.dumps(r),flush=True)
