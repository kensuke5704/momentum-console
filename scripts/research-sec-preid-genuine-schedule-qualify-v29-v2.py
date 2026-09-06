#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-legacy-etf-series-source-preid-v29genuine-2006.json'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(m);return m

base=load('genuine_base',ROOT/'scripts/research-sec-preid-genuine-schedule-qualify-v29.py')
grouping=load('grouping_v2',ROOT/'scripts/research-nq-hybrid-grouping-v29-v2.py')
summary_excluded=0
notes_excluded=0

_orig=grouping.legacy_grouped_schedule_blocks

def audited_grouping(primary_text: str, targets: dict):
    global summary_excluded,notes_excluded
    visible=grouping.h2diag.line_text(primary_text)
    for row in grouping.marker_filter_audit(visible,grouping.h2diag.SCHEDULE):
        if row.get('rejectionReason')=='SUMMARY_SCHEDULE_NOT_COMPLETE_PORTFOLIO': summary_excluded+=1
        elif row.get('rejectionReason')=='NOTES_REFERENCE': notes_excluded+=1
    return _orig(primary_text,targets)

grouping.legacy_grouped_schedule_blocks=audited_grouping
base.grouping=grouping


def main():
    base.main()
    d=json.loads(OUT.read_text())
    d['purpose']=(
        'Pre-Series-ID ETF source catalog requalified on genuine complete-portfolio headings only. '
        "'Notes to the Schedule of Investments' references and abbreviated 'Summary Schedule of Investments' "
        'tables are not accepted as complete-portfolio boundaries. Summary schedules disclose selected issuers '
        'plus aggregate other-securities rows and may explicitly state that the complete schedule is separately '
        'available. Each retained occurrence requires the exact normalized contemporaneous fund title at an '
        'accepted non-summary complete-holdings marker. No holdings names, ticker inference, future Series IDs, '
        'fuzzy matching, ranks, returns or strategy outcomes are used.'
    )
    d['genuineScheduleQualificationRule']='EXACT_NORMALIZED_PRE_ID_TITLE_AT_NON_NOTES_NON_SUMMARY_COMPLETE_HOLDINGS_MARKER'
    d['summaryScheduleExcludedMarkerCount']=summary_excluded
    d['notesReferenceExcludedMarkerCount']=notes_excluded
    OUT.write_text(json.dumps(d,indent=2)+'\n')
    print('QUALIFIER_V2',json.dumps({
        'positiveIdentityCount':d['positiveIdentityCount'],
        'sourceOccurrenceCount':d['sourceOccurrenceCount'],
        'rejectedIdentityCount':d['genuineRejectedIdentityCount'],
        'summaryScheduleExcludedMarkerCount':summary_excluded,
        'notesReferenceExcludedMarkerCount':notes_excluded,
        'fetchErrorCount':d['genuineScheduleFetchErrorCount'],
    }),flush=True)

if __name__=='__main__': main()
