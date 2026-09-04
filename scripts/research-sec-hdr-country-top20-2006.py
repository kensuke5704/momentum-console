#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json';PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json';OUT=ROOT/'data/research/sec-hdr-country-top20-2006.json'
SPEC=importlib.util.spec_from_file_location('hdr',ROOT/'scripts'/'research-sec-hdr-country-shard-2006.py');hdr=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(hdr)
def main():
 data=json.loads(COUNTRY.read_text());pit=json.loads(PIT.read_text());sf={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')};pop=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:20];rows=[]
 for i,r in enumerate(pop,1):
  x=hdr.resolve(r,sf);rows.append(x);print(f'{i}/{len(pop)}',json.dumps(x),flush=True)
 resolved=[r for r in rows if r['classification']!='UNKNOWN'];out={'purpose':'Top-20 weight diagnostic of the preregistered SEC .hdr.sgml PIT country resolver. Same rules as full shards; no result-dependent changes.','sampleCount':len(rows),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'rows':rows};OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
