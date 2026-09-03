#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v2',ROOT/'scripts/research-gate-b-aggregate-shadow-2020-v2.py');v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2);agg=v2.agg
man=json.loads((ROOT/'data/research/gate-b-production-source-manifest-2020.json').read_text())
rows=[]
for s in man['sources']:
 text,tr=agg.fetch(s['sourceDocumentUrl'])
 if s['seriesId']=='S000063326': hs,net=v2.extract_gfin(text,s['seriesName'])
 elif s['seriesId']=='S000061208': hs,net=v2.extract_ppty(text,s['seriesName'])
 else: hs,net=agg.extract_clearbridge(text,s['seriesName'])
 total=100*sum(v for _,v in hs)/net if net else None
 top10=100*sum(sorted((v for _,v in hs),reverse=True)[:10])/net if net else None
 r={'seriesId':s['seriesId'],'rows':len(hs),'netAssets':net,'totalWeight':total,'top10Weight':top10,'sample':[d for d,_ in hs[:10]],'transport':tr}
 rows.append(r);print('DIRECT',json.dumps(r),flush=True)
q=ROOT/'data/research/gate-b-aggregate-structure-diagnostic-2020.json';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps({'rows':rows,'purpose':'Direct structural extractor diagnostic. No Universe overlap/rank computed.'},indent=2)+'\n')
