#!/usr/bin/env python3
from __future__ import annotations

import html
import re

SCHEDULE = re.compile(r'SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS', re.I)
CATEGORY = re.compile(r'(?:^|\s)[—-]\s*\d+(?:\.\d+)?%|^TOTAL\b|^NET ASSETS?\b', re.I)
ROW_RE = re.compile(r'(?is)<TR\b[^>]*>(.*?)</TR>')
CELL_RE = re.compile(r'(?is)<T[DH]\b[^>]*>(.*?)</T[DH]>')
NUM = re.compile(r'^\(?\$?\s*[-+]?\d[\d,]*(?:\.\d+)?\s*\)?$')
HEADER = re.compile(r'^(?:SECURITY|DESCRIPTION|SHARES?|PRINCIPAL|VALUE|MARKET VALUE|COMMON STOCKS?|PREFERRED STOCKS?|SHORT[- ]TERM INVESTMENTS?)$', re.I)


def clean(raw: str) -> str:
    s = re.sub(r'(?is)<BR\s*/?>', ' ', raw)
    s = re.sub(r'(?is)<[^>]+>', ' ', s)
    return ' '.join(html.unescape(s).replace('\xa0', ' ').split())


def number(raw: str) -> float | None:
    s = raw.strip().replace('$', '').replace(',', '').replace(' ', '')
    negative = s.startswith('(') and s.endswith(')')
    if negative:
        s = s[1:-1]
    if not re.fullmatch(r'[-+]?\d+(?:\.\d+)?', s):
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def is_numeric(raw: str) -> bool:
    return bool(NUM.fullmatch(raw.strip())) and '%' not in raw and '/' not in raw


def rows(text: str) -> list[list[str]]:
    out = []
    for rm in ROW_RE.finditer(text):
        cells = [clean(x) for x in CELL_RE.findall(rm.group(1))]
        cells = [x for x in cells if x and x not in {'$', '—', '-', '–'}]
        if cells:
            out.append(cells)
    return out


def is_description(raw: str) -> bool:
    s = raw.strip()
    if len(s) < 2 or len(s) > 220 or not re.search(r'[A-Za-z]{2}', s):
        return False
    if HEADER.fullmatch(s) or CATEGORY.search(s):
        return False
    if re.match(r'^(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\b', s, re.I):
        return False
    return True


def parse_html_table(text: str) -> list[dict]:
    # Some legacy filings place the Schedule heading outside the HTML <TR> rows.
    # Start from the first row whenever the surrounding block itself is a schedule.
    started = bool(SCHEDULE.search(clean(text[:12000])))
    holdings = []
    seen = set()
    for cells in rows(text):
        joined = ' | '.join(cells)
        if SCHEDULE.search(joined):
            started = True
            continue
        if not started:
            continue

        numeric = [(i, number(c)) for i, c in enumerate(cells) if is_numeric(c)]
        numeric = [(i, v) for i, v in numeric if v is not None]
        if not numeric:
            continue

        # Market value is the rightmost positive numeric cell in ordinary legacy
        # Shares/Value schedules. Standalone subtotal rows have no issuer text and
        # are therefore rejected below.
        value_index, market_value = next(((i, v) for i, v in reversed(numeric) if v > 0), (None, None))
        if value_index is None or market_value is None:
            continue

        text_cells = [(i, c) for i, c in enumerate(cells[:value_index]) if is_description(c)]
        if not text_cells:
            continue
        desc_index, description = max(text_cells, key=lambda x: len(x[1]))
        if CATEGORY.search(description) or description.upper().startswith(('TOTAL ', 'NET ASSET')):
            continue

        # Quantity/principal normally sits after description and before market value.
        quantity = next((v for i, v in numeric if desc_index < i < value_index and v > 0), None)
        key = (description.upper(), quantity, market_value)
        if key in seen:
            continue
        seen.add(key)
        holdings.append({
            'description': description,
            'quantityOrPrincipal': quantity,
            'marketValue': market_value,
        })
    return holdings


def structural_sanity(holdings: list[dict]) -> bool:
    if not holdings:
        return False
    for h in holdings:
        desc = str(h.get('description') or '')
        value = float(h.get('marketValue') or 0)
        if not is_description(desc) or value <= 0:
            return False
        if re.fullmatch(r'20\d{2}', desc.strip()):
            return False
    return True
