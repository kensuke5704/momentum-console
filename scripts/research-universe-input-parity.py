#!/usr/bin/env python3
from __future__ import annotations
import gzip, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def eligible(f):
    si=re.compile(r'\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b',re.I)
    bb=re.compile(r'\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b',re.I)
    if si.search(f.get('seriesName','')) or bb.search(f.get('seriesName','')): return False
    hs=sorted([h for h in f.get('holdings',[]) if float(h.get('weight') or 0)>0],key=lambda h:-float(h.get('weight') or 0))
    return 10<=len(hs)<=120 and sum(float(h.get('weight') or 0) for h in hs)>=50 and sum(float(h.get('weight') or 0) for h in hs[:10])>=25

def latest(fs,asof):
    d={}
    for f in fs:
        if f.get('filingDate','')>asof: continue
        sid=f.get('seriesId',''); cur=d.get(sid)
        if cur is None or (f.get('filingDate',''),f.get('accession',''))>(cur.get('filingDate',''),cur.get('accession','')): d[sid]=f
    return [f for f in d.values() if eligible(f)]

def main():
    with gzip.open(ROOT/'data/sec-nport/bootstrap.json.gz','rt',encoding='utf-8') as fh: boot=json.load(fh)
    hist=json.loads((ROOT/'data/universe-history.json').read_text())
    months=hist.get('history',hist.get('months',[])) if isinstance(hist,dict) else hist
    p=next(x for x in months if x.get('signalMonth')=='2020-01')
    fs=boot.get('snapshots',boot) if isinstance(boot,dict) else boot
    calc=latest(fs,p['asOf'])
    prod={(x['seriesId'],x['accession']) for x in p.get('sourceFilings',[])}
    now={(x['seriesId'],x['accession']) for x in calc}
    allacc={x.get('accession') for x in fs}
    out={'asOf':p['asOf'],'prodSourceCount':len(prod),'calcSourceCount':len(now),'sourceIntersection':len(prod&now),'prodOnly':len(prod-now),'calcOnly':len(now-prod),'prodAccessionsPresentInBootstrap':sum(1 for _,a in prod if a in allacc),'prodFirst10Symbols':[x['symbol'] for x in p.get('symbols',[])[:10]],'prodOnlyExamples':sorted(prod-now)[:20],'calcOnlyExamples':sorted(now-prod)[:20]}
    print(json.dumps(out,indent=2))
    (ROOT/'data/research/universe-input-parity.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
