#!/usr/bin/env python3
from __future__ import annotations
import gzip, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/'data'/'universe-history.json'
BOOT=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'

hist=json.loads(HIST.read_text())
records=hist if isinstance(hist,list) else hist.get('records',hist.get('months',[]))
jan=next((r for r in records if r.get('signalMonth')=='2020-01'),None)
if not jan: raise RuntimeError('2020-01 not found')
with gzip.open(BOOT,'rt',encoding='utf-8') as f: boot=json.load(f)
filings=boot if isinstance(boot,list) else boot.get('filings',boot.get('records',[]))
by_acc={f.get('accession'):f for f in filings}
rows=[]
for s in jan.get('sourceFilings',[]):
    b=by_acc.get(s.get('accession'),{})
    rows.append({
      'accession':s.get('accession'), 'seriesId':s.get('seriesId'), 'seriesName':s.get('seriesName'), 'filingDate':s.get('filingDate'),
      'reportDate':b.get('reportDate'), 'holdingCount':len(b.get('holdings',[])) if isinstance(b.get('holdings'),list) else None
    })
print('SUMMARY',json.dumps({'signalMonth':'2020-01','asOf':jan.get('asOf'),'universeSize':len(jan.get('symbols',[])),'sourceSeriesCount':len(rows),'uniqueSeries':len({r['seriesId'] for r in rows})}),flush=True)
for r in rows: print('SERIES',json.dumps(r),flush=True)
