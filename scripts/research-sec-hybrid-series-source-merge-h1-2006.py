#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEGACY=ROOT/'data/research/sec-legacy-etf-series-source-preid-2006.json'
IDERA=ROOT/'data/research/sec-id-era-strict-series-source-h1-2006.json'
OUT=ROOT/'data/research/sec-hybrid-series-source-h1-2006.json'
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28'),('2006-03','2006-03-31'),('2006-04','2006-04-28'),('2006-05','2006-05-31'),('2006-06','2006-06-30')]

def norm(s): return ' '.join(re.sub(r'[^A-Z0-9]+',' ',html.unescape(s or '').upper()).split())

def main():
    legacy=json.loads(LEGACY.read_text());idera=json.loads(IDERA.read_text())
    legacy_ids=legacy['positiveIdentities'];id_series=idera['positiveSeries']
    by_legacy=defaultdict(list);by_id=defaultdict(list)
    for r in legacy_ids: by_legacy[(r['cik'],norm(r['seriesName']))].append(r)
    for r in id_series: by_id[(r['cik'],norm(r['seriesName']))].append(r)
    bridge={};ambiguous=[]
    for key,lrows in by_legacy.items():
        irows=by_id.get(key,[])
        if len(lrows)==1 and len(irows)==1:
            bridge[lrows[0]['legacyIdentity']]=irows[0]['seriesId']
        elif irows:
            ambiguous.append({'cik':key[0],'normalizedSeriesName':key[1],'legacyIdentities':[x['legacyIdentity'] for x in lrows],'seriesIds':[x['seriesId'] for x in irows]})
    mapped_series=set(bridge.values())
    source=[]
    for r in legacy['sourceOccurrences']:
        sid=bridge.get(r['legacyIdentity']);hybrid=f'SERIES:{sid}' if sid else r['legacyIdentity']
        source.append({'hybridIdentity':hybrid,'identityEra':'PRE_ID','legacyIdentity':r['legacyIdentity'],'seriesId':sid,'cik':r['cik'],'seriesName':r['seriesName'],'normalizedSeriesName':norm(r['seriesName']),'registrant':r['registrant'],'form':r['sourceForm'],'filingDate':r['sourceFilingDate'],'accession':r['sourceAccession'],'filename':r['sourceFilename'],'evidenceDateFiled':r['evidenceDateFiled'],'binding':r['binding']})
    for r in idera['sourceOccurrences']:
        source.append({'hybridIdentity':f"SERIES:{r['seriesId']}",'identityEra':'SERIES_ID','legacyIdentity':None,'seriesId':r['seriesId'],'cik':r['cik'],'seriesName':r['seriesName'],'normalizedSeriesName':norm(r['seriesName']),'registrant':r['company'],'form':r['form'],'filingDate':r['dateFiled'],'accession':r['accession'],'filename':r['filename'],'evidenceDateFiled':r['evidenceDateFiled'],'binding':r['binding']})
    snapshots=[]
    for month,asof in MONTHS:
        latest={}
        for r in source:
            if r['filingDate']>asof or r['evidenceDateFiled']>asof: continue
            cur=latest.get(r['hybridIdentity'])
            if cur is None or (r['filingDate'],r['accession'] or '',r['identityEra'])>(cur['filingDate'],cur['accession'] or '',cur['identityEra']): latest[r['hybridIdentity']]=r
        rows=sorted(latest.values(),key=lambda x:(x['cik'],x['normalizedSeriesName'],x['hybridIdentity']))
        snapshots.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(rows),'preIdSourceCount':sum(x['identityEra']=='PRE_ID' for x in rows),'seriesIdSourceCount':sum(x['identityEra']=='SERIES_ID' for x in rows),'sourceFilings':rows})
    out={'purpose':'PIT bridge between pre-Series-ID and Series-ID historical ETF source identities for 2006 H1. Bridge accepts only same-CIK exact-normalized Series/Fund names that are unique on both sides. No ticker, fuzzy, rename, holdings, rank, return, or strategy-outcome inference is used. Unmatched legacy identities remain separate and carry their latest public complete-portfolio source until a deterministically bridged Series-ID source supersedes them.','bridgeRule':'SAME_CIK_EXACT_NORMALIZED_NAME_UNIQUE_BOTH_SIDES','legacyPositiveIdentityCount':len(legacy_ids),'idEraPositiveSeriesCount':len(id_series),'exactBridgeCount':len(bridge),'bridgedSeriesIdCount':len(mapped_series),'ambiguousBridgeCount':len(ambiguous),'unmatchedLegacyIdentityCount':len(legacy_ids)-len(bridge),'unmatchedIdEraSeriesCount':len(id_series)-len(mapped_series),'bridge':bridge,'ambiguousBridges':ambiguous,'sourceOccurrenceCount':len(source),'sourceEraCounts':dict(Counter(r['identityEra'] for r in source)),'monthSnapshots':snapshots}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('bridge','ambiguousBridges','monthSnapshots')}),flush=True)
    for s in snapshots:print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount','preIdSourceCount','seriesIdSourceCount')}),flush=True)
if __name__=='__main__':main()
