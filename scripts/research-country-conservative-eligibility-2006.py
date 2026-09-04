#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-final-structural-merge-2006.json'
OUT=ROOT/'data/research/country-conservative-eligibility-2006.json'

def main():
 c=json.loads(COUNTRY.read_text());by=defaultdict(list)
 for h in c.get('rows',[]):
  by[h['seriesId']].append({'weight':float(h.get('weight') or 0),'classification':h.get('classification','UNKNOWN'),'description':h.get('description')})
 rows=[]
 for sid,hs in sorted(by.items()):
  us=[h for h in hs if h['classification']=='US'];usw=sum(h['weight'] for h in us);top10=sum(sorted((h['weight'] for h in us),reverse=True)[:10]);resolved=sum(h['weight'] for h in hs if h['classification']!='UNKNOWN');total=sum(h['weight'] for h in hs);eligible=(10<=len(us)<=120 and usw>=50 and top10>=25)
  rows.append({'seriesId':sid,'confirmedUsHoldingCount':len(us),'confirmedUsWeight':usw,'confirmedUsTop10Weight':top10,'resolvedCountryWeight':resolved,'totalEcWeight':total,'resolvedCountryWeightRate':resolved/total if total else None,'eligibleOnConfirmedUsOnly':eligible})
 n=sum(r['eligibleOnConfirmedUsOnly'] for r in rows)
 out={'purpose':'Conservative structural eligibility sensitivity using the frozen final holding-level country merge. Only confirmed US holdings count; UNKNOWN is excluded and never coerced. This measures whether remaining country uncertainty is material before freezing the historical bridge; it is not a return/performance test.','rule':'10-120 confirmed-US holdings, confirmed-US total weight >=50, confirmed-US top10 weight >=25.','seriesCount':len(rows),'eligibleSeriesCount':n,'eligibleSeriesRate':n/len(rows) if rows else None,'rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
 for r in rows:print('SERIES',json.dumps(r),flush=True)
if __name__=='__main__':main()
