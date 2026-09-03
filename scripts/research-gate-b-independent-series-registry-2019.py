#!/usr/bin/env python3
from __future__ import annotations
import csv,io,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/gate-b-independent-series-registry-2019.json'
URL='https://www.sec.gov/files/investment/data/other/investment-company-series-and-class-information/investment_company_series_class_2019.csv'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/csv,text/plain,*/*'}
TARGETS={'S000057700','S000063326','S000061208'}

def get():
 last=None
 for u in ('https://r.jina.ai/'+URL,URL):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=60) as r:return r.read(20_000_000).decode('utf-8-sig','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')

def pick(row,*names):
 for n in names:
  if n in row:return (row.get(n) or '').strip()
 low={k.lower().strip():k for k in row}
 for n in names:
  k=low.get(n.lower().strip())
  if k:return (row.get(k) or '').strip()
 return ''

def main():
 text,tr=get();lines=text.splitlines();start=0
 for i,x in enumerate(lines):
  if 'Series ID' in x and 'CIK' in x and ',' in x:start=i;break
 rows=list(csv.DictReader(io.StringIO('\n'.join(lines[start:]))));registry={}
 for r in rows:
  sid=pick(r,'Series ID','SERIES_ID');cik=pick(r,'CIK');sname=pick(r,'Series Name','SERIES_NAME');cname=pick(r,'Class Name','CLASS_NAME');ticker=pick(r,'Class Ticker','CLASS_TICKER');org=pick(r,'Organization Type','ORG_TYPE')
  if not re.fullmatch(r'S\d{9}',sid):continue
  naming=' '.join((sname,cname))
  if org and org!='30':continue
  if not ticker:continue
  if not re.search(r'(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED',naming,re.I):continue
  rec=registry.setdefault(sid,{'seriesId':sid,'cik':cik,'seriesName':sname,'classes':[]});rec['classes'].append({'className':cname,'ticker':ticker})
 vals=sorted(registry.values(),key=lambda x:x['seriesId']);found={x['seriesId']:x for x in vals if x['seriesId'] in TARGETS}
 out={'purpose':'Build an ETF-candidate series registry from the SEC 2019 Series/Class report without Production Universe inputs, then evaluate coverage of the three transition Production source series. Registry construction uses only SEC organization type, series/class names, and class ticker. No holdings, Universe ranks, or strategy returns are used.','sourceUrl':URL,'transport':tr,'registryCount':len(vals),'targetCount':len(TARGETS),'targetFoundCount':len(found),'targetCoverageRate':len(found)/len(TARGETS),'missingTargets':sorted(TARGETS-set(found)),'foundTargets':found,'registrySample':vals[:30]}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('foundTargets','registrySample')}),flush=True);print('FOUND',json.dumps(found),flush=True)
if __name__=='__main__':main()
# trigger 2026-09-03
