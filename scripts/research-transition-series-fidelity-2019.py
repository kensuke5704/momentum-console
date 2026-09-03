#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json,re,statistics
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-series-fidelity-2019.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
PIT_OUT=ROOT/'data/research/transition-nq-pit-2019.json'
pspec=importlib.util.spec_from_file_location('pit2019',ROOT/'scripts'/'research-transition-nq-pit-2019.py');pit=importlib.util.module_from_spec(pspec);pspec.loader.exec_module(pit)
def norm(s):
 s=(s or '').upper().replace('&',' AND ')
 s=re.sub(r'\s*\([A-Z0-9, ]{1,8}\)\s*$',' ',s)
 s=re.sub(r'\b(?:ADR|GDR)\b',' ',s)
 s=re.sub(r'\bCLASS\s+[A-Z0-9]+\b',' ',s)
 for a,b in [('INCORPORATED','INC'),('CORPORATION','CORP'),('COMPANY','CO'),('LIMITED','LTD'),('PLC','PLC')]:s=re.sub(rf'\b{a}\b',b,s)
 s=re.sub(r'\bTHE\b',' ',s)
 return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def earliest_nport(filings):
 d={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in d:d[sid]=f
 return d
def main():
 pit.main();legacy=json.loads(PIT_OUT.read_text())
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:boot=json.load(fh)
 filings=boot.get('snapshots',boot) if isinstance(boot,dict) else boot;first=earliest_nport(filings)
 rows=[]
 for r in legacy['records']:
  if not r.get('structurallyUsable'):continue
  nf=first.get(r.get('seriesId'))
  if not nf:continue
  nh=[{'name':norm(h.get('description')),'weight':float(h.get('weight') or 0),'raw':h.get('description')} for h in r.get('holdings',[]) if norm(h.get('description'))]
  ph=[{'name':norm(h.get('issuerName')),'weight':float(h.get('weight') or 0),'raw':h.get('issuerName')} for h in nf.get('holdings',[]) if norm(h.get('issuerName'))]
  pnames={h['name'] for h in ph};common=[h for h in nh if h['name'] in pnames]
  gap=None
  if r.get('reportDate') and nf.get('reportDate'):gap=(date.fromisoformat(nf['reportDate'])-date.fromisoformat(r['reportDate'])).days
  row={'seriesId':r['seriesId'],'seriesName':r.get('seriesName'),'ticker':(r.get('fundTickers') or [None])[0],'nqReportDate':r.get('reportDate'),'nportReportDate':nf.get('reportDate'),'daysBetweenReports':gap,'nqHoldings':len(nh),'nportHoldings':len(ph),'commonIssuerCount':len(common),'issuerCountOverlapRate':len(common)/len(nh) if nh else None,'nqWeightOverlapRate':sum(h['weight'] for h in common)/100 if nh else None}
  rows.append(row);print('PAIR',json.dumps(row),flush=True)
 valid=[r for r in rows if r['issuerCountOverlapRate'] is not None]
 gaps=[r['daysBetweenReports'] for r in valid if r['daysBetweenReports'] is not None]
 out={'purpose':'Gate B precursor rerun using corrected series-specific 2019 COMMON STOCKS parser. N-Q sources and target series were frozen before overlap inspection; no strategy returns used.','usableLegacySeries':len([r for r in legacy['records'] if r.get('structurallyUsable')]),'sameSeriesPairs':len(valid),'medianDaysBetweenReports':statistics.median(gaps) if gaps else None,'medianIssuerCountOverlapRate':statistics.median([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'minimumIssuerCountOverlapRate':min([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'medianNqWeightOverlapRate':statistics.median([r['nqWeightOverlapRate'] for r in valid]) if valid else None,'pairs':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='pairs'}),flush=True)
if __name__=='__main__':main()
