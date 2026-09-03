#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('nf',ROOT/'scripts'/'research-transition-nearest-fidelity-2019.py')
nf=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(nf)
OUT=ROOT/'data/research/firsttrust-schedule-boundary-diagnostic-2019.json'
TARGETS=['S000010977','S000017177','S000017178','S000033237','S000050385','S000044209','S000053942']

def main():
 rows=[]
 # Series names are known from early N-PORT bootstrap, not selected from overlap.
 import gzip
 with gzip.open(nf.BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;first=nf.earliest_nport(filings)
 names={sid:(first[sid].get('seriesName') or first[sid].get('fundName') or '') for sid in TARGETS if sid in first}
 groups={}
 for sid in TARGETS:
  if sid not in nf.CHOSEN or sid not in names:continue
  cik,acc,form,rd=nf.CHOSEN[sid];groups.setdefault((cik,acc,form),[]).append(sid)
 for (cik,acc,form),sids in groups.items():
  try: urls=nf.docs(cik,acc,form)
  except Exception as e:
   rows.append({'group':[cik,acc,form],'error':repr(e)});continue
  for url in urls:
   try:text,tr=nf.get(url)
   except Exception:continue
   ls=text.splitlines();markers=[i for i,x in enumerate(ls) if nf.SCHED_RE.search(x)]
   for m in markers[:80]:
    before=[]
    for sid,name in names.items():
     if sid not in sids:continue
     hits=[i for i in range(max(0,m-180),m+1) if name.lower() in ls[i].lower()]
     if hits:before.append({'seriesId':sid,'seriesName':name,'titleLine':hits[-1]+1,'distance':m-hits[-1]})
    if before:
     before.sort(key=lambda x:(x['distance'],x['seriesId']))
     window=[{'line':i+1,'text':ls[i]} for i in range(max(0,m-12),min(len(ls),m+35)) if ls[i].strip()]
     rows.append({'group':[cik,acc,form],'url':url,'transport':tr,'scheduleLine':m+1,'scheduleText':ls[m].strip(),'nearestRegisteredSeries':before[:4],'window':window})
 for r in rows:
  if 'scheduleLine' in r: print('BOUNDARY',json.dumps({k:v for k,v in r.items() if k!='window'}),flush=True)
 out={'purpose':'Structural diagnostic only: assign schedule markers to nearest preceding exact registered series title within 180 lines. No holdings overlap or strategy returns used.','targets':TARGETS,'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({'rows':len(rows),'markersWithRegisteredSeries':sum('scheduleLine'in r for r in rows)}),flush=True)
if __name__=='__main__':main()
