#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

v4 = load('final_v4_base', ROOT/'scripts/research-nq-pit-holdings-hybrid-h1-2006-v29final-v4.py')
hybrid = v4.hybrid

MONTH_ONLY = re.compile(r'^(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)$', re.I)
FINANCIAL_STATEMENT = re.compile(
    r'^(?:UNDISTRIBUTED\s+)?NET\s+(?:INVESTMENT\s+INCOME|REALIZED(?:\s+AND\s+UNREALIZED)?\s+GAIN)(?:\s*\(?(?:LOSS|ACCUMULATED\s+NET\s+REALIZED\s+LOSS)\)?)?$',
    re.I,
)
REPORT_LABEL = re.compile(
    r'^(?:DATE\s+OF\s+REPORTING\s+PERIOD|SIX\s+MONTHS\s+ENDED|SPECIAL\s+MEETING\s+OF\s+SHAREHOLDERS|'
    r'SHAREHOLDER\s+EXPENSES|ACCOUNT\s+VALUE|EXPENSE\s+RATIO|EXPENSES\s+PAID|TABLE\s+OF\s+CONTENTS)\b',
    re.I,
)
SUMMARY_AGGREGATE = re.compile(
    r'^(?:OTHER\s+ASSETS(?:\s+LESS\s+LIABILITIES)?|OTHER\s+LIABILITIES|OTHER\s+ASSETS\s+LESS\s+LIABILITIES|NET\s+ASSETS)$',
    re.I,
)


def structural_nonsecurity(desc: str) -> bool:
    text = ' '.join((desc or '').split())
    return bool(
        not text
        or MONTH_ONLY.fullmatch(text)
        or FINANCIAL_STATEMENT.fullmatch(text)
        or REPORT_LABEL.search(text)
        or SUMMARY_AGGREGATE.fullmatch(text)
        or v4.parser.BAD_TEXT_RE.search(text)
        or v4.parser.is_nonsecurity_text(text)
    )


def parsed_holdings_clean_all(combined: str):
    method, rows, _ = v4.html_first_clean_v4(combined)
    cleaned = []
    seen = set()
    for row in rows:
        desc = ' '.join(str(row.get('description') or '').split())
        value = max(0.0, float(row.get('marketValue') or 0.0))
        if structural_nonsecurity(desc) or value <= 0:
            continue
        key = (desc, row.get('quantityOrPrincipal'), value)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({**row, 'description': desc, 'marketValue': value})
    cleaned = v4.parser.drop_page_split_suffix_duplicates(cleaned)
    total = sum(float(r.get('marketValue') or 0.0) for r in cleaned)
    if total > 0:
        for row in cleaned:
            row['weight'] = 100.0 * float(row['marketValue']) / total
        cleaned.sort(key=lambda r: float(r.get('weight') or 0.0), reverse=True)
    return method + '_structural_sanitize_v5', cleaned, total


hybrid.corrected.parsed_holdings = parsed_holdings_clean_all
hybrid.annotate_sections = v4.annotate_sections_fast_exact
hybrid.legacy_grouped_schedule_blocks = v4.grouping.legacy_grouped_schedule_blocks
hybrid.seg.grouped_schedule_blocks = v4.grouping.series_grouped_schedule_blocks

if __name__ == '__main__':
    hybrid.main()
