#!/usr/bin/env python3
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data/universe-history.json'
d=json.loads(p.read_text())

def walk(x):
    if isinstance(x,dict):
        if x.get('signalMonth'):
            yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x,list):
        for v in x:
            yield from walk(v)

records=list(walk(d))
print('STRUCTURE',json.dumps({'topType':type(d).__name__,'topKeys':list(d.keys())[:20] if isinstance(d,dict) else None,'signalMonthRecords':len(records),'firstMonths':[x.get('signalMonth') for x in records[:5]]}),flush=True)
r=next((x for x in records if x.get('signalMonth')=='2020-01'),None)
if r is None: raise SystemExit('2020-01 not found after recursive structure scan')
print('SUMMARY',json.dumps({'signalMonth':r.get('signalMonth'),'asOf':r.get('asOf'),'symbolCount':len(r.get('symbols',[])),'sourceFilings':len(r.get('sourceFilings',[]))}),flush=True)
for f in r.get('sourceFilings',[]): print('SOURCE',json.dumps(f),flush=True)
for s in r.get('symbols',[]): print('SYMBOL',json.dumps({k:s.get(k) for k in ['symbol','universeRank','etfCount','aggregateWeight','maxWeight','recencyWeight','universeScore']}),flush=True)
