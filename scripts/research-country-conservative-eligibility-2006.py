#!/usr/bin/env python3
from __future__ import annotations
import json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'data/research/nq-npx-structural-mapping-2006.json'
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
ADD=ROOT/'data/research/structural-new-matches-country-2006.json'
OUT=ROOT/'data/research/country-conservative-eligibility-2006.json'

def main():
 m=json.loads(MAP.read_text());c=json.loads(COUNTRY.read_text());a=json.loads(ADD.read_text())
 cls={(r['ticker'],r['securityId']):r.get('classification','UNKNOWN') for r in c.get('identityRows',[])}
 for r in a.get('rows',[]):
  if r.get('classification')!='UNKNOWN':cls[(r['ticker'],r['securityId'])]=r['classification']
 by=defaultdict(list)
 for d in m.get('details',[]):
  state='UNKNOWN';ids=d.get('identities') or []
  if len(ids)==1:state=cls.get((ids[0].get('ticker'),ids[0].get('securityId')),'UNKNOWN')
  if state=='UNKNOWN' and re.search(r'\b(?:ADR|GDR|ADS)\b',d.get('description',''),re.I):state='NON_US'
  by[d['seriesId']].append({'weight':float(d.get('weight') or 0),'classification':state,'description':d.get('description')})
 rows=[]
 for sid,hs in sorted(by.items()):
  us=[h for h in hs if h['classification']=='US'];usw=sum(h['weight'] for h in us);top10=sum(sorted((h['weight'] for h in us),reverse=True)[:10]);resolved=sum(h['weight'] for h in hs if h['classification']!='UNKNOWN');total=sum(h['weight'] for h in hs);eligible=(10<=len(us)<=120 and usw>=50 and top10>=25)
  rows.append({'seriesId':sid,'confirmedUsHoldingCount':len(us),'confirmedUsWeight':usw,'confirmedUsTop10Weight':top10,'resolvedCountryWeight':resolved,'totalEcWeight':total,'eligibleOnConfirmedUsOnly':eligible})
 out={'purpose':'Sensitivity baseline only: apply Production-style structural eligibility using only holdings already confirmed US by the conservative PIT hierarchy. UNKNOWN is excluded, never coerced. This measures whether country coverage is still material before freezing the bridge; it does not define the final historical Universe.','rule':'10-120 confirmed-US holdings, confirmed-US total weight >=50, confirmed-US top10 weight >=25. Existing structural name exclusions remain upstream.','seriesCount':len(rows),'eligibleSeriesCount':sum(r['eligibleOnConfirmedUsOnly'] for r in rows),'eligibleSeriesRate':sum(r['eligibleOnConfirmedUsOnly'] for r in rows)/len(rows) if rows else None,'rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
 for r in rows:print('SERIES',json.dumps(r),flush=True)
if __name__=='__main__':main()
