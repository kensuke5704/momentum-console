#!/usr/bin/env python3
from __future__ import annotations
import gzip,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
HIST=ROOT/'data/universe-history.json'
OUT=ROOT/'data/research/gate-b-transition-source-coverage-2020.json'

# Metadata-only exact-series legacy mappings already frozen before holdings fidelity inspection.
LEGACY_SERIES={
'S000010977','S000017177','S000017178','S000033237','S000050385','S000044209',
'S000053942','S000053943','S000053944','S000053945','S000053946','S000053947','S000053948',
'S000047480','S000050191','S000031813','S000055090','S000059263',
'S000038223','S000051284','S000051348','S000053021','S000053022','S000058619'
}

def months(raw):
 if isinstance(raw,list):return raw
 if isinstance(raw,dict):
  for k in ('months','history'):
   if isinstance(raw.get(k),list):return raw[k]
  return [v for v in raw.values() if isinstance(v,dict) and v.get('signalMonth')]
 return []

def main():
 hist=json.loads(HIST.read_text())
 m=next(x for x in months(hist) if x.get('signalMonth')=='2020-01')
 prod_sources=m.get('sourceFilings',[])
 prod_sids=[x.get('seriesId') for x in prod_sources if x.get('seriesId')]
 covered=[x for x in prod_sources if x.get('seriesId') in LEGACY_SERIES]
 missing=[x for x in prod_sources if x.get('seriesId') not in LEGACY_SERIES]
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 snaps=b.get('snapshots',b) if isinstance(b,dict) else b
 first_by_sid={}
 for f in sorted(snaps,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in first_by_sid:first_by_sid[sid]=f
 rows=[]
 for src in prod_sources:
  sid=src.get('seriesId');f=first_by_sid.get(sid,{})
  rows.append({'seriesId':sid,'seriesName':src.get('seriesName') or f.get('seriesName'),'accession':src.get('accession') or f.get('accession'),'filingDate':src.get('filingDate'),'earliestNportReportDate':f.get('reportDate'),'legacyExactSeriesAvailable':sid in LEGACY_SERIES,'nportHoldings':len(f.get('holdings',[]))})
 out={'purpose':'Determine whether the already frozen metadata-only legacy transition cohort covers the actual 2020-01 Production source filings before attempting aggregate Gate B reconstruction. No holdings overlap or returns used for source selection.', 'signalMonth':'2020-01','productionUniverseSize':len(m.get('symbols',[])),'productionSourceFilings':len(prod_sources),'productionUniqueSeries':len(set(prod_sids)),'legacyCoveredSourceFilings':len(covered),'legacyCoverageRate':len(covered)/len(prod_sources) if prod_sources else None,'coveredSeriesIds':[x.get('seriesId') for x in covered],'missingSeries':missing,'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('missingSeries','rows')}),flush=True)
 for r in rows:print('SOURCE',json.dumps(r),flush=True)
if __name__=='__main__':main()
