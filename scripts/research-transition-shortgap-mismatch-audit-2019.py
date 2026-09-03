#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
S=importlib.util.spec_from_file_location('sg',ROOT/'scripts'/'research-transition-shortgap-fidelity-2019.py')
sg=importlib.util.module_from_spec(S);S.loader.exec_module(sg);n=sg.nearest

def first(filings):
 d={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in d:d[sid]=f
 return d
with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
filings=b.get('snapshots',b) if isinstance(b,dict) else b;fs=first(filings)
names={sid:(fs.get(sid,{}).get('seriesName') or fs.get(sid,{}).get('fundName') or '') for sid in sg.nearest.CHOSEN}
cache={}
for sid,(cik,acc,form,rd) in sg.nearest.CHOSEN.items():
 nf=fs.get(sid);name=names.get(sid)
 if not nf or not name:continue
 key=(cik,acc,form)
 if key not in cache:
  du=n.docs(cik,acc,form);cache[key]=[(u,n.locate_doc([u],name)) for u in du]
 hits=[]
 for u,hit in cache[key]:
  if hit and n.structural_start(hit[3].splitlines(),name) is not None:hits.append(hit)
 hit=sorted(hits,key=lambda x:(x[0],x[1]),reverse=True)[0] if hits else n.locate_doc([u for u,_ in cache[key]],name)
 if not hit:continue
 text=hit[3];same=[names[x] for x,v in sg.nearest.CHOSEN.items() if v[:3]==(cik,acc,form) and names.get(x)]
 seg=n.slice_series(text,name,same)
 legacy=sg.parse_name_first_us(seg)
 ph=[{'raw':h.get('issuerName') or '','name':n.norm(h.get('issuerName') or ''),'symbol':h.get('symbol'),'weight':h.get('weight')} for h in nf.get('holdings',[]) if h.get('issuerName')]
 ln={x['name'] for x in legacy};pn={x['name'] for x in ph}
 lo=[x['raw'] for x in legacy if x['name'] not in pn]
 po=[{'issuer':x['raw'],'symbol':x['symbol'],'weight':x['weight']} for x in ph if x['name'] not in ln]
 print('SERIES',json.dumps({'seriesId':sid,'seriesName':name,'legacyUS':len(legacy),'nport':len(ph),'common':len(ln&pn),'legacyOnly':lo,'nportOnly':po},ensure_ascii=False),flush=True)
