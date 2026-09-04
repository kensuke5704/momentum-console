#!/usr/bin/env python3
from __future__ import annotations
import glob,json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data/research'
BASE=D/'country-full-coverage-unknown-retry-2006.json';MAP=D/'nq-npx-structural-mapping-2006.json';ADD=D/'structural-new-matches-country-2006.json';OUT=D/'country-filing-index-merged-2006.json'
ROUTE_GLOBS=['sec-hdr-country-shard-*-2006.json','sec-hdr-country-top20-2006.json','sec-filing-date-country-shard-*-2006.json','sec-issuer-name-filing-date-country-shard-*-2006.json','sec-known-cik-filing-index-country-2006.json','sec-filing-date-country-fast-2006.json','sec-filing-date-country-pilot-2006.json','sec-filing-index-country-pilot-2006.json']
def key(r):return (str(r.get('ticker') or ''),str(r.get('securityId') or ''))
def main():
 base=json.loads(BASE.read_text());mp=json.loads(MAP.read_text());add=json.loads(ADD.read_text())
 frozen={key(r):r.get('classification','UNKNOWN') for r in base.get('identityRows',[])}
 evidence=defaultdict(list)
 for r in add.get('rows',[]):
  if r.get('classification') in ('US','NON_US'):evidence[key(r)].append({'classification':r['classification'],'source':'STRUCTURAL_ADDITION_COUNTRY','stateCode':r.get('stateCode')})
 files=[]
 for pat in ROUTE_GLOBS:
  for f in glob.glob(str(D/pat)):
   files.append(f);obj=json.loads(Path(f).read_text())
   for r in obj.get('rows',[]):
    if r.get('classification') in ('US','NON_US'):evidence[key(r)].append({'classification':r['classification'],'source':r.get('resolutionSource') or Path(f).name,'stateCode':r.get('stateCode'),'cutoff':r.get('countryEvidenceCutoff')})
 merged={};conflicts=[]
 allkeys=set(frozen)|set(evidence)
 for k in allkeys:
  f=frozen.get(k,'UNKNOWN')
  if f in ('US','NON_US'):
   vals={e['classification'] for e in evidence.get(k,[])}
   if vals and any(v!=f for v in vals):conflicts.append({'ticker':k[0],'securityId':k[1],'frozen':f,'laterEvidence':evidence[k]})
   merged[k]=f;continue
  vals={e['classification'] for e in evidence.get(k,[])}
  if len(vals)==1:merged[k]=next(iter(vals))
  elif len(vals)>1:merged[k]='CONFLICT';conflicts.append({'ticker':k[0],'securityId':k[1],'frozen':'UNKNOWN','laterEvidence':evidence[k]})
  else:merged[k]='UNKNOWN'
 by=defaultdict(list);counts=defaultdict(int);weights=defaultdict(float)
 for d in mp.get('details',[]):
  st='UNKNOWN';ids=d.get('identities') or []
  if len(ids)==1:st=merged.get((str(ids[0].get('ticker') or ''),str(ids[0].get('securityId') or '')),'UNKNOWN')
  if st in ('UNKNOWN','CONFLICT') and re.search(r'\b(?:ADR|GDR|ADS)\b',d.get('description',''),re.I):st='NON_US'
  w=float(d.get('weight') or 0);counts[st]+=1;weights[st]+=w;by[d['seriesId']].append((w,st))
 total_n=sum(counts.values());total_w=sum(weights.values());resolved_n=counts['US']+counts['NON_US'];resolved_w=weights['US']+weights['NON_US']
 series=[]
 for sid,hs in sorted(by.items()):
  us=[w for w,s in hs if s=='US'];usw=sum(us);top10=sum(sorted(us,reverse=True)[:10]);series.append({'seriesId':sid,'confirmedUsHoldingCount':len(us),'confirmedUsWeight':usw,'confirmedUsTop10Weight':top10,'eligibleOnConfirmedUsOnly':10<=len(us)<=120 and usw>=50 and top10>=25,'resolvedCountryWeight':sum(w for w,s in hs if s in ('US','NON_US')),'totalEcWeight':sum(w for w,s in hs)})
 out={'purpose':'Merge frozen country baseline, deterministic structural mapping additions and preregistered historical SEC country routes, including accession header SGML. Existing resolved classifications are frozen. Multiple new routes must agree; disagreements remain CONFLICT and are not counted as resolved. Explicit ADR/GDR/ADS may only add NON_US evidence when otherwise unresolved. No returns/ranks used.','inputRouteFiles':sorted(set(Path(f).name for f in files)),'conflictCount':len(conflicts),'conflicts':conflicts,'allEcClassificationCounts':dict(counts),'allEcClassificationWeights':dict(weights),'allEcResolvedCountRate':resolved_n/total_n if total_n else None,'allEcResolvedWeightRate':resolved_w/total_w if total_w else None,'eligibleSeriesConfirmedUsOnly':sum(r['eligibleOnConfirmedUsOnly'] for r in series),'seriesCount':len(series),'series':series}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('conflicts','series')}),flush=True)
if __name__=='__main__':main()
