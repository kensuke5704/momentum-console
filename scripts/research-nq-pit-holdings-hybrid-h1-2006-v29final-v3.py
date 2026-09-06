#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(m);return m

v2=load('final_v2_base',ROOT/'scripts/research-nq-pit-holdings-hybrid-h1-2006-v29final-v2.py')
parser=v2.parser
hybrid=v2.hybrid
grouping=load('grouping_v29_v2_for_holdings',ROOT/'scripts/research-nq-hybrid-grouping-v29-v2.py')


def html_first_clean_parsed_holdings(combined: str) -> tuple[str,list[dict],float]:
    """Preserve valid HTML rows, exclude explicit financial-statement text, then use fixed-width only if needed."""
    trimmed=parser.corrected.trim_series_schedule(combined)
    html_rows=parser.base.parse_bound_html_holdings(trimmed)
    if html_rows:
        out=[];seen=set()
        for holding in html_rows:
            desc=' '.join(str(holding.get('description') or '').split())
            value=max(0.0,float(holding.get('marketValue') or 0.0))
            quantity=holding.get('quantityOrPrincipal')
            if not desc or value<=0: continue
            if parser.BAD_TEXT_RE.search(desc): continue
            key=(desc,quantity,value)
            if key in seen: continue
            seen.add(key)
            out.append({'description':desc,'marketValue':value,'quantityOrPrincipal':quantity})
        out=parser.drop_page_split_suffix_duplicates(out)
        if out:
            total=sum(row['marketValue'] for row in out)
            for row in out: row['weight']=100.0*row['marketValue']/total
            out.sort(key=lambda row:row['weight'],reverse=True)
            return 'schedule_bound_html_preserved_financial_text_filtered',out,total
    # Zero-only structural fallback. Summary schedules are already excluded at grouping.
    return parser.parsed_holdings(combined)

hybrid.corrected.parsed_holdings=html_first_clean_parsed_holdings
hybrid.legacy_grouped_schedule_blocks=grouping.legacy_grouped_schedule_blocks
hybrid.seg.grouped_schedule_blocks=grouping.series_grouped_schedule_blocks

if __name__=='__main__': hybrid.main()
