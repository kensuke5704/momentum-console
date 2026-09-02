#!/usr/bin/env python3
"""Run the 13F/N-PORT pilot with scale-invariant PERMCO↔ticker price matching.

The underlying 13F mirror stores contemporaneous raw prices, while current Yahoo
history can retroactively reflect later stock splits. A constant multiplicative
price scale therefore carries no identifier information. We estimate that scale
from all common quarter-end observations, then compare residual path error.
Thresholds and all universe logic are unchanged.
"""
from __future__ import annotations
import importlib.util
import statistics
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pilot_base',HERE/'research-hf13f-nport-pilot.py')
base=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(base)

def build_mapping(price_by,symbols):
    quarters=['2022Q1','2022Q2','2022Q3','2022Q4','2023Q1','2023Q2','2023Q3','2023Q4']
    stored=base.repo_prices(); mapped={}; details={}
    for si,sym in enumerate(sorted(symbols),1):
        yr=base.yahoo_raw(sym); source='yahoo'
        if len(yr)<4:
            yr=base.repo_rows(stored,sym); source='repo-fallback'
        obs={q:base.nearest_close(yr,base.qend(q)) for q in quarters}; obs={q:p for q,p in obs.items() if p}
        best=[]
        if len(obs)>=4:
            for perm,pp in price_by.items():
                common=[q for q in obs if q in pp and pp[q]>0]
                if len(common)<4: continue
                # Remove a constant price-scale difference caused by later split back-adjustment.
                scale=statistics.median([pp[q]/obs[q] for q in common])
                errs=[abs(pp[q]-scale*obs[q])/max(pp[q],scale*obs[q]) for q in common]
                med=statistics.median(errs); mx=max(errs)
                if med<=0.02: best.append((med,mx,-len(common),perm,scale))
        best.sort(); accepted=None
        if best:
            b=best[0]; second=best[1] if len(best)>1 else None
            if b[0]<=0.01 and (second is None or second[0]>=max(0.015,b[0]*2)): accepted=b[3]
        if accepted: mapped[accepted]=sym
        details[sym]={
            'permco':accepted,
            'bestMedianRelativeError':best[0][0] if best else None,
            'runnerUpError':best[1][0] if len(best)>1 else None,
            'points':-best[0][2] if best else 0,
            'estimatedPriceScale':best[0][4] if best else None,
            'priceSource':source,
        }
        if si%25==0: print('MAPPING',si,'/',len(symbols),'accepted',sum(1 for x in details.values() if x['permco']),flush=True)
        time.sleep(.02)
    return mapped,details

base.build_mapping=build_mapping
base.main()
