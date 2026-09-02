#!/usr/bin/env python3
import gzip,json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
with gzip.open(P,'rt',encoding='utf-8') as f:d=json.load(f)
rows=d.get('snapshots') or d.get('filings') or []
by={}
for x in rows:
    rd=str(x.get('reportDate') or '')
    if not rd.startswith('2020'):continue
    sid=str(x.get('seriesId') or '')
    if not sid:continue
    r=by.setdefault(sid,{'seriesId':sid,'seriesName':x.get('seriesName'),'reports':[],'holdingCountMax':0})
    r['seriesName']=r['seriesName'] or x.get('seriesName')
    r['reports'].append({'reportDate':x.get('reportDate'),'filingDate':x.get('filingDate')})
    r['holdingCountMax']=max(r['holdingCountMax'],len(x.get('holdings',[])))
vals=sorted(by.values(),key=lambda r:((r.get('seriesName') or ''),r['seriesId']))
print('SERIES_COUNT',len(vals))
for r in vals:
    name=str(r.get('seriesName') or '')
    if re.search(r'SPDR|ISHARES|INVESCO|POWERSHARES|PROSHARES|FIRST TRUST|VANGUARD|ETF',name,re.I):
        print(json.dumps(r,sort_keys=True))
