#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/research/sec-hybrid-etf-source-catalog-h1-2006.json'
SHARDS=ROOT/'data/research/shards'
OUT=ROOT/'data/research/nq-pit-holdings-hybrid-h1-2006.json'


def source_key(month,row,output=False):
    return (
        month,
        row.get('canonicalIdentity'),
        row.get('sourceFilename') if output else row.get('filename'),
        row.get('filingDate'),
    )


def main():
    catalog=json.loads(CAT.read_text())
    paths=sorted(SHARDS.glob('nq-pit-holdings-hybrid-h1-2006-shard-*.json'))
    if len(paths)!=4: raise SystemExit(f'expected 4 shard files, got {len(paths)}')
    shards=[json.loads(p.read_text()) for p in paths]

    records={}; duplicate=[]
    for sh in shards:
      for snap in sh['monthSnapshots']:
        for row in snap['sourceFilings']:
          k=source_key(snap['signalMonth'],row,True)
          if k in records: duplicate.append(k)
          records[k]=row
    if duplicate: raise SystemExit(f'duplicate merged source keys: {duplicate[:10]}')

    snaps=[]
    for snap in catalog['monthSnapshots']:
      month=snap['signalMonth']; rows=[]; missing=[]
      for src in snap['sourceFilings']:
        k=source_key(month,src,False); row=records.get(k)
        if row is None:
          missing.append({'canonicalIdentity':src.get('canonicalIdentity'),'sourceFilename':src.get('filename'),'filingDate':src.get('filingDate')})
        else: rows.append(row)
      rows.sort(key=lambda x:(x.get('canonicalIdentity') or '',x.get('sourceFilename') or ''))
      snaps.append({
        'signalMonth':month,'asOf':snap['asOf'],
        'catalogSourceSeriesCount':snap['sourceSeriesCount'],
        'catalogLegacySourceCount':snap.get('legacySourceCount'),
        'catalogSeriesIdSourceCount':snap.get('seriesIdSourceCount'),
        'parsedSourceSeriesCount':sum(x.get('parseStatus')=='PARSED' for x in rows),
        'parsedLegacySourceCount':sum(x.get('parseStatus')=='PARSED' and x.get('identityRegime')=='LEGACY_PRE_ID' for x in rows),
        'parsedSeriesIdSourceCount':sum(x.get('parseStatus')=='PARSED' and x.get('identityRegime')=='SERIES_ID' for x in rows),
        'missingParsedSeries':missing,'sourceFilings':rows,
      })
      print('MERGED_MONTH',json.dumps({'signalMonth':month,'catalog':snap['sourceSeriesCount'],'records':len(rows),'missing':len(missing)}),flush=True)

    section_counts=Counter(); section_weights=defaultdict(float)
    audits=[]
    for sh in shards:
      section_counts.update(sh.get('legacyAssetSectionCounts') or {})
      for k,v in (sh.get('legacyAssetSectionWeights') or {}).items(): section_weights[k]+=float(v or 0)
      audits.extend(sh.get('filingAudit') or [])

    out={
      'purpose':'Authoritative source-v5 H1 2006 holdings reconstruction merged from four deterministic filing shards. Each unique source filing is assigned to exactly one shard by sorted source-key index modulo four. Parser, source identity, grouping and asset-section semantics are identical across shards; merge order cannot affect assignment.',
      'sourceCatalogPath':'data/research/sec-hybrid-etf-source-catalog-h1-2006.json',
      'sourceCatalogRunId':34022850269,
      'uniqueSourceFilingCount':sum(int(s.get('uniqueSourceFilingCount') or 0) for s in shards),
      'legacyRequestedIdentityCount':sum(int(s.get('legacyRequestedIdentityCount') or 0) for s in shards),
      'seriesIdRequestedIdentityCount':sum(int(s.get('seriesIdRequestedIdentityCount') or 0) for s in shards),
      'filingFetchSuccessCount':sum(int(s.get('filingFetchSuccessCount') or 0) for s in shards),
      'filingFetchErrorCount':sum(int(s.get('filingFetchErrorCount') or 0) for s in shards),
      'legacyAssignmentRule':shards[0].get('legacyAssignmentRule'),
      'seriesIdAssignmentRule':shards[0].get('seriesIdAssignmentRule'),
      'legacyAssetSectionRule':shards[0].get('legacyAssetSectionRule'),
      'uniqueParsedHoldingCount':sum(int(s.get('uniqueParsedHoldingCount') or 0) for s in shards),
      'legacyAssetSectionCounts':dict(section_counts),
      'legacyAssetSectionWeights':dict(section_weights),
      'eligibilityStatus':shards[0].get('eligibilityStatus'),
      'filingAudit':sorted(audits,key=lambda x:(x.get('filename') or '',x.get('accession') or '')),
      'monthSnapshots':snaps,
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('MERGE_SUMMARY',json.dumps({k:out[k] for k in ('uniqueSourceFilingCount','legacyRequestedIdentityCount','seriesIdRequestedIdentityCount','filingFetchSuccessCount','filingFetchErrorCount','uniqueParsedHoldingCount','legacyAssetSectionCounts')}),flush=True)

if __name__=='__main__': main()
