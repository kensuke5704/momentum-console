#!/usr/bin/env python3
from __future__ import annotations

import gzip, importlib.util, json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BOOT=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
OUT=ROOT/'data'/'research'/'legacy-unmatched-holdings-diagnostic-2020.json'

fspec=importlib.util.spec_from_file_location('fast',ROOT/'scripts'/'research-legacy-universe-reproducibility-fast-2020.py')
fast=importlib.util.module_from_spec(fspec); fspec.loader.exec_module(fast)
repro=fast.repro

FIX={'company':'First Trust Exchange-Traded Fund VI','dateFiled':'2020-12-07','filename':'edgar/data/1552740/0001445546-20-005815.txt'}
transport,submission=repro.ov.fetch_full_filing(repro.ov.seg.meta.sec_url(FIX['filename']))
rm=repro.ov.REPORT_DATE.search(submission); report=repro.ov.iso8(rm.group(1) if rm else None)
# Use the exact frozen Production-side series identity set, as the successful
# Gate-A fixture does. This avoids depending on SGML SERIES tags surviving Jina
# text flattening; no holdings or scores are used to choose identities.
series=fast.shared_nport_series_contracts(submission,FIX['company'])
mapped=fast.structural_mapped_modern_series(repro.ov.embedded_csr(submission),series)
with gzip.open(BOOT,'rt',encoding='utf-8') as f: bp=json.load(f)
by=defaultdict(list)
for f in bp.get('snapshots') or bp.get('filings') or []:
    if f.get('seriesId') and f.get('reportDate'): by[f['seriesId']].append(f)

rows=[]
for sid,row in mapped.items():
    cand=by.get(sid,[])
    if not cand: continue
    nearest=min(cand,key=lambda f:repro.days_between(report,f['reportDate']))
    gap=repro.days_between(report,nearest['reportDate'])
    if gap>45: continue
    alias_map=repro.unique_alias_symbol_map(nearest.get('holdings',[]))
    legacy_matched=set(); unmatched=[]
    for h in row.get('holdings',[]):
        w=float(h.get('weight') or 0); desc=str(h.get('description') or '')
        if w<=0: continue
        symbol=None; aliases=repro.issuer_aliases(desc)
        for a in aliases:
            if a in alias_map: symbol=alias_map[a]; break
        if symbol: legacy_matched.add(symbol)
        else: unmatched.append({'description':desc,'weight':w,'aliases':aliases[:8]})
    nport_only=[]
    for h in nearest.get('holdings',[]):
        sym=str(h.get('symbol') or '').strip().upper(); w=float(h.get('weight') or 0)
        if sym and w>0 and sym not in legacy_matched:
            nport_only.append({'symbol':sym,'issuerName':h.get('issuerName'),'weight':w,'aliases':repro.issuer_aliases(str(h.get('issuerName') or ''))[:8]})
    unmatched.sort(key=lambda x:-x['weight']); nport_only.sort(key=lambda x:-x['weight'])
    rows.append({'seriesId':sid,'seriesName':row.get('seriesName'),'reportDate':report,'nportReportDate':nearest.get('reportDate'),'unmatchedLegacy':unmatched[:30],'nportOnly':nport_only[:30]})

out={'purpose':'Structural diagnosis of unmatched issuer identities on fixed paired 2020 series. No prices, returns, ranks, or strategy outcomes are used to change mapping rules.','transport':transport,'fixture':FIX,'reportDate':report,'series':rows}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('PAIRED_DIAGNOSTIC_SERIES',len(rows))
for r in rows:
    print('SERIES',r['seriesId'],r['seriesName'])
    print('NPORT_ONLY',json.dumps(r['nportOnly'][:15],sort_keys=True))
    print('UNMATCHED_LEGACY',json.dumps(r['unmatchedLegacy'][:15],sort_keys=True))
