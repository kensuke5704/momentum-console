#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

v2 = load('grouping_v2_base', ROOT / 'scripts/research-nq-hybrid-grouping-v29-v2.py')
hybrid=v2.hybrid
seg=v2.seg
h2diag=v2.h2diag
legacy=v2.legacy

COMPLETE_AVAILABLE_RE=re.compile(
    r"(?:THE\s+)?FUND[’'S\s]+COMPLETE\s+SCHEDULE\s+OF\s+INVESTMENTS\s+IS\s+AVAILABLE|"
    r"COMPLETE\s+SCHEDULE\s+OF\s+INVESTMENTS\s+IS\s+AVAILABLE",
    re.I,
)
OTHER_SECURITIES_DEF_RE=re.compile(
    r"OTHER\s+SECURITIES\s+ARE\s+THOSE\s+SECURITIES.*?(?:50\s+LARGEST|ONE\s+PERCENT)",
    re.I|re.S,
)
SUMMARY_HEADING_FLEX_RE=re.compile(
    r"S\s*U\s*M\s*M\s*A\s*R\s*Y\s+S\s*C\s*H\s*E\s*D\s*U\s*L\s*E(?:S)?\s+O\s*F\s+I\s*N\s*V\s*E\s*S\s*T\s*M\s*E\s*N\s*T\s*S",
    re.I,
)


def normalized_visible(text:str)->str:
    return ' '.join(h2diag.line_text(text).split())


def block_is_abbreviated_summary(block:str)->bool:
    visible=normalized_visible(block)
    # Either an explicit (possibly letter-spaced) Summary Schedule heading, or the
    # shareholder-report disclosure that only selected issuers are printed and the
    # complete schedule is separately available. The latter is unique structural
    # evidence that the table is not a complete portfolio.
    if SUMMARY_HEADING_FLEX_RE.search(visible):
        return True
    if COMPLETE_AVAILABLE_RE.search(visible) and (
        OTHER_SECURITIES_DEF_RE.search(visible) or re.search(r'\bOTHER\s+SECURITIES\b',visible,re.I)
    ):
        return True
    return False


def series_grouped_schedule_blocks(primary_text: str, series: list[dict]) -> tuple[dict[str,list[str]],list[dict]]:
    markers=v2.valid_markers(primary_text,h2diag.SCHEDULE)
    grouped:dict[str,list[str]]={};audit=[]
    for idx,marker in enumerate(markers):
        start=marker.start();end=markers[idx+1].start() if idx+1<len(markers) else min(len(primary_text),start+300000)
        block=primary_text[start:end]
        assigned,rule=seg.assign_marker_series(primary_text,marker,series)
        if block_is_abbreviated_summary(block):
            audit.append({'markerIndex':idx,'marker':seg.visible(marker.group(0)),'assignmentRule':'SUMMARY_SCHEDULE_NOT_COMPLETE_PORTFOLIO_BLOCK','seriesId':assigned.get('seriesId') if assigned else None,'seriesName':assigned.get('seriesName') if assigned else None})
            continue
        audit.append({'markerIndex':idx,'marker':seg.visible(marker.group(0)),'assignmentRule':rule,'seriesId':assigned.get('seriesId') if assigned else None,'seriesName':assigned.get('seriesName') if assigned else None})
        if assigned and assigned.get('seriesId'):
            grouped.setdefault(assigned['seriesId'],[]).append(block)
    return grouped,audit


def legacy_grouped_schedule_blocks(primary_text:str,targets:dict[str,dict])->tuple[dict[str,list[str]],list[dict]]:
    visible=h2diag.line_text(primary_text)
    markers=v2.valid_markers(visible,h2diag.SCHEDULE)
    target_by_norm={row['normalizedSeriesName']:iid for iid,row in targets.items()}
    grouped:dict[str,list[str]]=defaultdict(list);audit=[];carry:str|None=None
    for idx,marker in enumerate(markers):
        next_start=markers[idx+1].start() if idx+1<len(markers) else len(visible)
        before=visible[max(0,marker.start()-1800):marker.start()].splitlines()[-18:]
        after=visible[marker.end():min(len(visible),marker.end()+1800)].splitlines()[:18]
        window={'markerIndex':idx,'marker':marker.group(0),'beforeLines':before,'afterLines':after}
        candidates=legacy.title_candidates(window)
        exact=sorted({target_by_norm[c['normalizedTitle']] for c in candidates if c['normalizedTitle'] in target_by_norm})
        meaningful=sorted({c['normalizedTitle'] for c in candidates})
        start=max(0,marker.start()-1600)
        block=visible[start:next_start]
        if block_is_abbreviated_summary(block):
            carry=None
            audit.append({'markerIndex':idx,'marker':marker.group(0),'candidateTitles':meaningful,'exactTargetIdentities':exact,'assignedIdentity':None,'assignmentRule':'SUMMARY_SCHEDULE_NOT_COMPLETE_PORTFOLIO_BLOCK'})
            continue
        rule='UNASSIGNED';assigned=None
        if len(exact)==1:
            carry=exact[0];assigned=carry;rule='EXACT_NORMALIZED_TITLE_AT_MARKER'
        elif len(exact)>1:
            carry=None;rule='AMBIGUOUS_EXACT_TARGETS'
        elif meaningful:
            carry=None;rule='DIFFERENT_MEANINGFUL_TITLE_BOUNDARY'
        elif carry:
            assigned=carry;rule='UNTITLED_CONTINUATION_OF_EXACT_TARGET'
        if assigned:
            actual_start=max(0,marker.start()-1600) if rule=='EXACT_NORMALIZED_TITLE_AT_MARKER' else marker.start()
            actual_block=visible[actual_start:next_start]
            if block_is_abbreviated_summary(actual_block):
                carry=None;assigned=None;rule='SUMMARY_SCHEDULE_NOT_COMPLETE_PORTFOLIO_BLOCK'
            else:
                grouped[assigned].append(actual_block)
        audit.append({'markerIndex':idx,'marker':marker.group(0),'candidateTitles':meaningful,'exactTargetIdentities':exact,'assignedIdentity':assigned,'assignmentRule':rule})
    return dict(grouped),audit
