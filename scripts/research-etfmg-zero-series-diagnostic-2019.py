#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('sg',ROOT/'scripts'/'research-transition-shortgap-fidelity-2019.py')
sg=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(sg)
OUT=ROOT/'data/research/etfmg-zero-series-diagnostic-2019.json'
TARGETS=['S000051284','S000051348','S000058619']
URL='https://www.sec.gov/Archives/edgar/data/1467831/000089418919008202/etfmg_n-csr.htm'

def main():
 text,tr=sg.nearest.get(URL);ls=text.splitlines()
 import gzip
 with gzip.open(sg.nearest.BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;first=sg.nearest.earliest_nport(filings)
 rows=[]
 all_names=[(first[s].get('seriesName') or first[s].get('fundName') or '') for s in sg.nearest.CHOSEN if s in first]
 for sid in TARGETS:
  name=first[sid].get('seriesName') or first[sid].get('fundName') or ''
  hits=[i for i,x in enumerate(ls) if name.lower() in x.lower()]
  detail={'seriesId':sid,'seriesName':name,'titleHits':[i+1 for i in hits]}
  windows=[]
  for i in hits:
   lo=max(0,i-10);hi=min(len(ls),i+260)
   sched=[j for j in range(i,hi) if re.search(r'(?:Portfolio|Schedule) of Investments',ls[j],re.I)]
   common=[j for j in range(i,hi) if re.search(r'\bCOMMON STOCKS?\b',ls[j],re.I)]
   if sched or common:
    windows.append({'titleLine':i+1,'scheduleLines':[j+1 for j in sched[:5]],'commonStockLines':[j+1 for j in common[:5]],'window':[{'line':j+1,'text':ls[j]} for j in range(lo,min(hi,i+120)) if ls[j].strip()]})
  detail['windows']=windows
  # Also show existing slicer's size and parser counts, without using overlap.
  seg=sg.nearest.slice_series(text,name,all_names)
  detail['existingSegmentLines']=len(seg.splitlines()) if seg else 0
  detail['nameFirstRows']=len(sg.parse_name_first(seg)) if seg else 0
  rows.append(detail)
  print('SERIES',json.dumps({k:v for k,v in detail.items() if k!='windows'}),flush=True)
 out={'purpose':'Structural diagnosis of three fixed short-gap series that produced zero rows. No overlap or performance used to alter selection.','transport':tr,'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
