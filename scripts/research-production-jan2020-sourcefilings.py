#!/usr/bin/env python3
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data/universe-history.json'
d=json.loads(p.read_text())
records=d.get('records',d.get('months',d if isinstance(d,list) else [])) if isinstance(d,dict) else d
if isinstance(records,dict): records=list(records.values())
r=next((x for x in records if x.get('signalMonth')=='2020-01'),None)
if r is None: raise SystemExit('2020-01 not found')
print('SUMMARY',json.dumps({'signalMonth':r.get('signalMonth'),'asOf':r.get('asOf'),'symbolCount':len(r.get('symbols',[])),'sourceFilings':len(r.get('sourceFilings',[]))}),flush=True)
for f in r.get('sourceFilings',[]): print('SOURCE',json.dumps(f),flush=True)
for s in r.get('symbols',[]): print('SYMBOL',json.dumps({k:s.get(k) for k in ['symbol','universeRank','etfCount','aggregateWeight','maxWeight','recencyWeight','universeScore']}),flush=True)
