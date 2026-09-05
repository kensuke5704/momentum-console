#!/usr/bin/env python3
from __future__ import annotations

import html
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEGACY=ROOT/'data/research/sec-legacy-etf-series-source-q4-2005.json'
OUT=ROOT/'data/research/sec-legacy-series-line-binding-diagnostic-2005.json'

def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load_module('base',ROOT/'scripts/research-sec-historical-etf-series-source-catalog-h1-2006.py')
diag=load_module('diag',ROOT/'scripts/research-nq-legacy-series-title-diagnostic-q4-2005.py')
CLASS=re.compile(r'\b(?:VIPER(?:\s+SHARES?)?|ETF\s+SHARES?|EXCHANGE[- ]TRADED\s+SHARES?)\b',re.I)
BRAND=re.compile(r'\b(?:ISHARES|STREETTRACKS|SPDR|ETF|EXCHANGE[- ]TRADED)\b',re.I)

def lines(raw):
 s=re.sub(r'(?is)<(?:br|p|div|tr|td|th|li|h[1-6])\b[^>]*>','\n',raw)
 s=re.sub(r'(?is)</(?:p|div|tr|td|th|li|h[1-6])>','\n',s)
 s=re.sub(r'(?is)<[^>]+>',' ',s);s=html.unescape(s).replace('\xa0',' ')
 return [' '.join(x.split()) for x in s.splitlines() if ' '.join(x.split())]

def main():
 data=json.loads(LEGACY.read_text());by=defaultdict(list)
 for r in data['legacySeries']:by[r['evidenceFilename']].append(r)
 outrows=[];errors=[]
 for fn,rows in sorted(by.items()):
  try:
   raw,tr,_,prior=base.ft(base.su(fn),4_000_000,22);ls=lines(raw);nls=[base.norm(x) for x in ls]
   class_idx=[i for i,x in enumerate(ls) if CLASS.search(x)]
   for r in rows:
    title=r['normalizedSeriesName'];hits=[i for i,x in enumerate(nls) if title and title in x]
    nearest=min((abs(i-j) for i in hits for j in class_idx),default=None)
    snippets=[]
    for i in hits[:5]:snippets.append({'lineIndex':i,'lines':ls[max(0,i-2):min(len(ls),i+3)]})
    outrows.append({
     'legacyIdentity':r['legacyIdentity'],'cik':r['cik'],'registrant':r['registrant'],'seriesName':r['seriesName'],
     'normalizedSeriesName':title,'evidenceFilename':fn,'titleOccurrenceLineCount':len(hits),
     'nearestExplicitEtfClassLineDistance':nearest,'sameOrAdjacentExplicitEtfClass':nearest is not None and nearest<=1,
     'within2LinesExplicitEtfClass':nearest is not None and nearest<=2,'titleHasEtfSemanticBrand':bool(BRAND.search(title)),
     'isRegistrantName':title==base.norm(r['registrant']),'titleSnippets':snippets,'transport':tr,'priorErrors':prior
    })
  except Exception as e:errors.append({'filename':fn,'error':type(e).__name__,'detail':str(e)[:600]})
 result={'purpose':'Line-level structural diagnostic for strict pre-Series-ID ETF Series binding. A mixed-trust title should not inherit Creation Unit evidence merely because it appears elsewhere in the same prospectus. Measure whether the exact title line is same/adjacent to an explicit VIPER/ETF Shares label, while separately flagging titles whose own contemporaneous wording is explicitly ETF-semantic. Registrant-name rows are flagged. No holdings, later Series IDs, ranks, returns, or strategy outcomes are used.','source':'LEGACY_SERIES_LINE_BINDING_DIAGNOSTIC_V1','seriesCount':len(outrows),'filingErrorCount':len(errors),'sameOrAdjacentExplicitEtfClassCount':sum(x['sameOrAdjacentExplicitEtfClass'] for x in outrows),'within2LinesExplicitEtfClassCount':sum(x['within2LinesExplicitEtfClass'] for x in outrows),'titleHasEtfSemanticBrandCount':sum(x['titleHasEtfSemanticBrand'] for x in outrows),'registrantNameCount':sum(x['isRegistrantName'] for x in outrows),'diagnostics':outrows,'errors':errors}
 OUT.write_text(json.dumps(result,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in result.items() if k not in ('diagnostics','errors')}),flush=True)
 for x in outrows:print('SERIES',json.dumps({k:x[k] for k in ('cik','seriesName','nearestExplicitEtfClassLineDistance','sameOrAdjacentExplicitEtfClass','within2LinesExplicitEtfClass','titleHasEtfSemanticBrand','isRegistrantName')}),flush=True)
if __name__=='__main__':main()
