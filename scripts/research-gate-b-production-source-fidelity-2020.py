#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json,statistics
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DISC=ROOT/'data/research/gate-b-production-source-legacy-discovery-2020.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
OUT=ROOT/'data/research/gate-b-production-source-fidelity-2020.json'
SPEC=importlib.util.spec_from_file_location('near',ROOT/'scripts'/'research-transition-nearest-fidelity-2019.py')
near=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(near)

def earliest(filings):
 out={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in out:out[sid]=f
 return out

def main():
 d=json.loads(DISC.read_text())
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;first=earliest(filings)
 all_names=[r.get('seriesName','') for r in d.get('rows',[]) if r.get('seriesName')]
 rows=[]
 for r in d.get('rows',[]):
  sid=r.get('seriesId');chosen=r.get('chosenLegacy');nf=first.get(sid)
  rec={'seriesId':sid,'seriesName':r.get('seriesName'),'status':'NO_LEGACY' if not chosen else 'PENDING'}
  if not chosen or not nf:
   rows.append(rec);print('PAIR',json.dumps(rec),flush=True);continue
  cik=chosen.get('registrantCik');acc=chosen.get('accession');form=chosen.get('form');rd=chosen.get('reportDate')
  try:
   urls=near.docs(str(int(cik)),acc,form);hit=near.locate_doc(urls,r.get('seriesName',''))
   if not hit:
    rec.update({'status':'NO_DOCUMENT','legacyReportDate':rd});rows.append(rec);print('PAIR',json.dumps(rec),flush=True);continue
   score,nchars,url,text,tr=hit;seg=near.slice_series(text,r.get('seriesName',''),all_names)
   if not seg:
    ls=text.splitlines();hs=[i for i,x in enumerate(ls) if r.get('seriesName','').lower() in x.lower()]
    for i in hs:
     if near.SCHED_RE.search('\n'.join(ls[i:min(len(ls),i+15)])):
      seg='\n'.join(ls[i:min(len(ls),i+2200)]);break
   grammar,lh=near.parse_rows(seg)
   p=[{'name':near.norm(h.get('issuerName') or ''),'weight':float(h.get('weight') or 0)} for h in nf.get('holdings',[]) if h.get('issuerName')]
   lnames={h['name'] for h in lh};ret=[x for x in p if x['name'] in lnames]
   gap=(date.fromisoformat(nf['reportDate'])-date.fromisoformat(rd)).days
   rec.update({'status':'PARSED' if lh else 'PARSE_EMPTY','legacyForm':form,'legacyReportDate':rd,'nportReportDate':nf.get('reportDate'),'daysBetweenReports':gap,'parserGrammar':grammar,'legacyHoldings':len(lh),'nportHoldings':len(p),'nportRetainedCount':len(ret),'nportRetentionRate':len(ret)/len(p) if p else None,'documentUrl':url,'documentScore':score})
  except Exception as e:rec.update({'status':'ERROR','error':repr(e)})
  rows.append(rec);print('PAIR',json.dumps(rec),flush=True)
 valid=[x for x in rows if x.get('nportRetentionRate') is not None]
 out={'purpose':'Actual Production 2020-01 source-series fidelity audit using metadata-only selected nearest legacy filings. Directional retention asks whether filtered early-NPORT issuer identities can be found in the earlier legacy common-stock schedule; no strategy returns or universe ranks used.','sourceCount':len(rows),'parsedPairs':len(valid),'medianDaysBetweenReports':statistics.median([x['daysBetweenReports'] for x in valid]) if valid else None,'medianNportRetentionRate':statistics.median([x['nportRetentionRate'] for x in valid]) if valid else None,'minimumNportRetentionRate':min([x['nportRetentionRate'] for x in valid]) if valid else None,'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
