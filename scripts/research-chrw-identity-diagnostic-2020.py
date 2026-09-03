#!/usr/bin/env python3
from __future__ import annotations

import gzip, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BOOTSTRAP=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
OUT=ROOT/'data'/'research'/'chrw-identity-diagnostic-2020.json'

spec=importlib.util.spec_from_file_location('fast',ROOT/'scripts'/'research-legacy-universe-reproducibility-fast-2020.py')
fast=importlib.util.module_from_spec(spec); spec.loader.exec_module(fast)

FIXTURE={
 'company':'First Trust Exchange-Traded Fund VI',
 'filename':'edgar/data/1552740/0001445546-20-005815.txt',
 'dateFiled':'2020-12-07',
}

def main():
    with gzip.open(BOOTSTRAP,'rt',encoding='utf-8') as f: bp=json.load(f)
    rows=bp.get('snapshots') or bp.get('filings') or []
    nport=[]
    target_sids=set()
    for r in rows:
        hits=[]
        for h in r.get('holdings',[]):
            if str(h.get('symbol') or '').upper()=='CHRW':
                hits.append({'issuerName':h.get('issuerName'),'symbol':h.get('symbol'),'weight':h.get('weight')})
        if hits:
            target_sids.add(str(r.get('seriesId') or ''))
            nport.append({'seriesId':r.get('seriesId'),'seriesName':r.get('seriesName'),'reportDate':r.get('reportDate'),'filingDate':r.get('filingDate'),'hits':hits})

    transport,submission=fast.repro.ov.fetch_full_filing(fast.repro.ov.seg.meta.sec_url(FIXTURE['filename']))
    # Use frozen identities here only to locate the same paired series already used by Gate A.
    series=fast.shared_nport_series_contracts(submission,FIXTURE['company'])
    mapped=fast.structural_mapped_modern_series(fast.repro.ov.embedded_csr(submission),series)
    legacy=[]
    for sid,row in mapped.items():
        if sid not in target_sids: continue
        likely=[]
        for h in row.get('holdings',[]):
            d=str(h.get('description') or '')
            u=''.join(ch for ch in d.upper() if ch.isalnum() or ch==' ')
            if 'ROBINSON' in u or 'CH ROBINSON' in u.replace(' ',''):
                likely.append({'description':d,'weight':h.get('weight')})
        legacy.append({'seriesId':sid,'seriesName':row.get('seriesName'),'likelyLegacyDescriptions':likely})

    out={'purpose':'Diagnose only the CHRW issuer-name structural identity mismatch observed in the paired-series Universe comparison. No prices, returns, trades, or strategy performance are used.',
         'transport':transport,'nport':nport,'legacy':legacy}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__': main()
