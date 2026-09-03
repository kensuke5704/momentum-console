#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/research/country-full-coverage-raw-header-2006.json'
STRUCT=ROOT/'data/research/structural-new-matches-country-2006.json'
OUT=ROOT/'data/research/country-consolidated-structural-raw-2006.json'

def main():
 raw=json.loads(RAW.read_text());st=json.loads(STRUCT.read_text())
 allc=dict(raw['allEcHoldingClassificationCounts']);allw=dict(raw['allEcHoldingClassificationWeights'])
 added={'US':0,'NON_US':0,'UNKNOWN':0};addedw={'US':0.0,'NON_US':0.0,'UNKNOWN':0.0}
 rows=st.get('results',st.get('rows',[]))
 # structural-new artifact contains only identities newly mapped by structural rules; baseline raw merge has none of these rows.
 for r in rows:
  cls=r.get('classification','UNKNOWN');occ=int(r.get('occurrenceCount') or 1);w=float(r.get('aggregateWeight') or r.get('weight') or 0)
  if cls not in added:cls='UNKNOWN'
  added[cls]+=occ;addedw[cls]+=w
 # These holdings were part of all-EC UNKNOWN before mapping; move only resolved structural additions out of UNKNOWN.
 resolved_occ=added['US']+added['NON_US'];resolved_w=addedw['US']+addedw['NON_US']
 allc['UNKNOWN']-=resolved_occ;allc['US']+=added['US'];allc['NON_US']+=added['NON_US']
 allw['UNKNOWN']-=resolved_w;allw['US']+=addedw['US'];allw['NON_US']+=addedw['NON_US']
 totalc=sum(allc.values());totalw=sum(allw.values())
 out={'year':2006,'purpose':'Consolidated conservative country coverage over all 936 EC holdings: baseline PIT attribution + UNKNOWN 10-K retry + raw historical SEC-header validation + independently resolved structural mapping additions. No UNKNOWN coercion, current-state evidence, returns, or ranks.','rawHeaderArtifactBase':raw.get('purpose'),'structuralNewClassificationCounts':added,'structuralNewClassificationWeights':addedw,'structuralResolvedAddedCount':resolved_occ,'structuralResolvedAddedWeight':resolved_w,'allEcHoldingClassificationCounts':allc,'allEcHoldingClassificationWeights':allw,'allEcResolvedCountRate':(allc['US']+allc['NON_US'])/totalc,'allEcResolvedWeightRate':(allw['US']+allw['NON_US'])/totalw}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps(out),flush=True)
if __name__=='__main__':main()
