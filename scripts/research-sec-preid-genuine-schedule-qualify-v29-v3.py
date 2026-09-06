#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-legacy-etf-series-source-preid-v29genuine-2006.json'


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader is not None;s.loader.exec_module(m);return m

base=load('genuine_base_v3',ROOT/'scripts/research-sec-preid-genuine-schedule-qualify-v29.py')
grouping=load('grouping_v3',ROOT/'scripts/research-nq-hybrid-grouping-v29-v3.py')
counts=Counter();by_call=[]
_orig=grouping.legacy_grouped_schedule_blocks

def audited(primary_text,targets):
    grouped,audit=_orig(primary_text,targets)
    c=Counter(x.get('assignmentRule') for x in audit)
    counts.update(c)
    by_call.append({
        'summaryBlockRejectedMarkerCount':c.get('SUMMARY_SCHEDULE_NOT_COMPLETE_PORTFOLIO_BLOCK',0),
        'ambiguousAssignedMarkerCount':sum(bool(x.get('assignmentRule')=='AMBIGUOUS_EXACT_TARGETS' and x.get('assignedIdentity')) for x in audit),
    })
    return grouped,audit

grouping.legacy_grouped_schedule_blocks=audited
base.grouping=grouping


def main():
    base.main()
    d=json.loads(OUT.read_text())
    audits=d.get('genuineScheduleAudit',[])
    for rec,extra in zip(audits,by_call): rec.update(extra)
    d['purpose']=(
      'Pre-Series-ID ETF source catalog requalified on genuine complete-portfolio headings and blocks only. '
      "Notes references and abbreviated shareholder-report Summary Schedules are rejected. Summary blocks are "
      "also recognized by their contemporaneous disclosure that the Fund's complete schedule of investments is "
      'available separately together with aggregate Other securities rows. Each retained occurrence requires the '
      'exact normalized contemporaneous fund title at an accepted complete-portfolio block. No holdings-name '
      'inference, ticker inference, future Series IDs, fuzzy matching, ranks, returns, or strategy outcomes are used.'
    )
    d['genuineScheduleQualificationRule']='EXACT_NORMALIZED_PRE_ID_TITLE_AT_NON_NOTES_NON_SUMMARY_COMPLETE_HOLDINGS_BLOCK'
    d['summaryScheduleRejectedBlockMarkerCount']=counts.get('SUMMARY_SCHEDULE_NOT_COMPLETE_PORTFOLIO_BLOCK',0)
    d['ambiguousAssignedMarkerCount']=sum(x.get('ambiguousAssignedMarkerCount',0) for x in by_call)
    d['genuineScheduleAudit']=audits
    OUT.write_text(json.dumps(d,indent=2)+'\n')
    impacted=[{'accession':x.get('accession'),'filename':x.get('filename'),'filingDate':x.get('filingDate'),'summaryBlockRejectedMarkerCount':x.get('summaryBlockRejectedMarkerCount')} for x in audits if x.get('summaryBlockRejectedMarkerCount')]
    print('QUALIFIER_V3',json.dumps({'positiveIdentityCount':d['positiveIdentityCount'],'sourceOccurrenceCount':d['sourceOccurrenceCount'],'rejectedIdentityCount':d['genuineRejectedIdentityCount'],'summaryScheduleRejectedBlockMarkerCount':d['summaryScheduleRejectedBlockMarkerCount'],'ambiguousAssignedMarkerCount':d['ambiguousAssignedMarkerCount'],'fetchErrorCount':d['genuineScheduleFetchErrorCount'],'summaryImpactedFilings':impacted}),flush=True)
    if d['genuineScheduleFetchErrorCount']: raise SystemExit('pre-ID qualifier v3 fetch errors')
    if d['ambiguousAssignedMarkerCount']: raise SystemExit('ambiguous marker assigned')

if __name__=='__main__': main()
