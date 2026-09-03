#!/usr/bin/env python3
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data/research/nq-npx-mapping-2006.json'
d=json.loads(p.read_text())
rows=d.get('details',[])
print('SUMMARY',json.dumps({'details':len(rows),'topKeys':list(d.keys()),'detailKeys':sorted({k for r in rows for k in r.keys()})}),flush=True)
for r in rows[:5]: print('ROW',json.dumps(r),flush=True)
