#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRE=Path(os.environ.get('LEGACY_CATALOG_PATH',str(ROOT/'data/research/sec-legacy-etf-series-source-preid-2006.json')))
POST=Path(os.environ.get('ID_CATALOG_PATH',str(ROOT/'data/research/sec-id-era-strict-series-source-h1-2006.json')))
OUT=ROOT/'data/research/sec-hybrid-etf-source-catalog-h1-2006.json'
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28'),('2006-03','2006-03-31'),('2006-04','2006-04-28'),('2006-05','2006-05-31'),('2006-06','2006-06-30')]

def norm(s): return ' '.join(re.sub(r'[^A-Z0-9]+',' ',html.unescape(s or '').upper()).split())

def main():
    pre=json.loads(PRE.read_text());post=json.loads(POST.read_text())
    legacy=pre['positiveIdentities'];series=post['positiveSeries']
    series_by_id={r['seriesId']:r for r in series}
    legacy_by_key=defaultdict(list);series_by_key=defaultdict(list)
    for r in legacy: legacy_by_key[(r['cik'],r['normalizedSeriesName'])].append(r)
    for r in series: series_by_key[(r['cik'],norm(r['seriesName']))].append(r)
    bridge={};amb=[]
    for key,lvals in legacy_by_key.items():
        svals=series_by_key.get(key,[])
        if len(lvals)==1 and len(svals)==1: bridge[lvals[0]['legacyIdentity']]=svals[0]['seriesId']
        elif svals: amb.append({'cik':key[0],'normalizedSeriesName':key[1],'legacyCount':len(lvals),'seriesIdCount':len(svals),'legacyIdentities':[x['legacyIdentity'] for x in lvals],'seriesIds':[x['seriesId'] for x in svals]})
    reverse_bridge={v:k for k,v in bridge.items()}
    pre_occ=pre['sourceOccurrences'];post_occ=post['sourceOccurrences']
    snapshots=[]
    for month,asof in MONTHS:
        legacy_latest={}
        for r in pre_occ:
            if r['sourceFilingDate']>asof or r['evidenceDateFiled']>asof: continue
            cur=legacy_latest.get(r['legacyIdentity'])
            if cur is None or (r['sourceFilingDate'],r.get('sourceAccession') or '')>(cur['sourceFilingDate'],cur.get('sourceAccession') or ''): legacy_latest[r['legacyIdentity']]=r
        post_latest={}
        for r in post_occ:
            ev=series_by_id.get(r['seriesId'])
            if not ev or ev['evidenceDateFiled']>asof or r['dateFiled']>asof: continue
            cur=post_latest.get(r['seriesId'])
            if cur is None or (r['dateFiled'],r.get('accession') or '')>(cur['dateFiled'],cur.get('accession') or ''): post_latest[r['seriesId']]=r
        rows=[];suppressed=[]
        for lid,r in legacy_latest.items():
            sid=bridge.get(lid)
            if sid and sid in post_latest:
                suppressed.append({'legacyIdentity':lid,'seriesId':sid,'reason':'EXACT_UNIQUE_NAME_BRIDGE_HAS_POST_ID_SOURCE'})
                continue
            rows.append({'canonicalIdentity':sid or lid,'identityRegime':'LEGACY_PRE_ID','legacyIdentity':lid,'seriesId':sid,'seriesName':r['seriesName'],'normalizedSeriesName':r['normalizedSeriesName'],'cik':r['cik'],'registrant':r['registrant'],'form':r['sourceForm'],'filingDate':r['sourceFilingDate'],'accession':r.get('sourceAccession'),'filename':r['sourceFilename'],'evidenceDateFiled':r['evidenceDateFiled'],'binding':r['binding'],'sourceInventoryPeriod':'2005H2_OR_2006_PRE_ID'})
        for sid,r in post_latest.items():
            ev=series_by_id[sid]
            rows.append({'canonicalIdentity':sid,'identityRegime':'SERIES_ID','legacyIdentity':reverse_bridge.get(sid),'seriesId':sid,'seriesName':r['seriesName'],'normalizedSeriesName':norm(r['seriesName']),'cik':r['cik'],'registrant':r['company'],'form':r['form'],'filingDate':r['dateFiled'],'accession':r.get('accession'),'filename':r['filename'],'evidenceDateFiled':ev['evidenceDateFiled'],'binding':ev['binding'],'sourceInventoryPeriod':'2006H1'})
        ids=[r['canonicalIdentity'] for r in rows]
        if len(ids)!=len(set(ids)): raise RuntimeError(f'duplicate canonical identity in {month}')
        rows=sorted(rows,key=lambda x:(x['cik'],x['canonicalIdentity'],x['filingDate'],x.get('accession') or ''))
        snapshots.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(rows),'legacySourceCount':sum(r['identityRegime']=='LEGACY_PRE_ID' for r in rows),'seriesIdSourceCount':sum(r['identityRegime']=='SERIES_ID' for r in rows),'suppressedLegacyCount':len(suppressed),'sourceFilings':rows,'suppressedLegacy':suppressed})
    out={'purpose':'Hybrid PIT ETF source catalog across the 2006-02-06 SEC Series/Class-ID regime boundary. Pre-ID identities are bridged to post-ID Series IDs only by same-CIK, exact normalized Series/Fund name, unique on both sides. No ticker, fuzzy, rename, holdings, rank, return, or strategy-outcome inference is used. A bridged legacy source is suppressed only once the corresponding Series ID has its own eligible public complete-portfolio source by that month end.','source':'HYBRID_PRE_ID_COMPLETE_PORTFOLIO_PLUS_STRICT_SERIES_ID_V2','bridgeRule':'SAME_CIK + EXACT_NORMALIZED_NAME + UNIQUE_BOTH_SIDES','legacyPositiveIdentityCount':len(legacy),'postIdPositiveSeriesCount':len(series),'exactUniqueBridgeCount':len(bridge),'ambiguousBridgeCount':len(amb),'ambiguousBridges':amb,'bridges':[{'legacyIdentity':k,'seriesId':v} for k,v in sorted(bridge.items())],'monthSnapshots':snapshots}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('ambiguousBridges','bridges','monthSnapshots')}),flush=True)
    for s in snapshots: print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount','legacySourceCount','seriesIdSourceCount','suppressedLegacyCount')}),flush=True)
if __name__=='__main__':main()
