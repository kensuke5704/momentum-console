#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/sec-marketwide-nq-inventory-q1-2006.json'
SHARD_INDEX = int(os.environ.get('SHARD_INDEX', '0'))
SHARD_COUNT = int(os.environ.get('SHARD_COUNT', '1'))
OUT = ROOT / f'data/research/sec-marketwide-series-class-q1-2006-shard-{SHARD_INDEX:02d}.json'
INVENTORY_ARTIFACT_ID = 9945162305
UA = {
    'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research',
    'Accept': 'text/html,text/plain,*/*',
    'Accept-Encoding': 'identity',
}
SID_RE = re.compile(r'\b(S\d{9})\b', re.I)
CID_RE = re.compile(r'\b(C\d{9})\b', re.I)
TICKER_RE = re.compile(r'^[A-Z][A-Z0-9.\-]{0,9}$')
HTML_ROW_RE = re.compile(r'(?is)<tr\b[^>]*>(.*?)</tr>')
HTML_CELL_RE = re.compile(r'(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>')
HTML_TAG_RE = re.compile(r'(?is)<[^>]+>')
MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\([^\)]+\)')


def fetch_one(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read(1_500_000)
    return payload.decode('utf-8', 'replace')


def clean_text(value: str) -> str:
    return ' '.join(html.unescape(value).replace('\xa0', ' ').split())


def clean_html_cell(value: str) -> str:
    return clean_text(HTML_TAG_RE.sub(' ', value))


def after_markdown_link(line: str, ident: str) -> str:
    match = re.search(rf'\[{re.escape(ident)}\]\([^\)]+\)(.*)$', line, re.I)
    if match:
        return clean_text(match.group(1))
    pos = line.upper().find(ident.upper())
    if pos >= 0:
        return clean_text(line[pos + len(ident):].lstrip(' ]()'))
    return ''


def meaningful_after_identifier(cells: list[str], ident_index: int) -> list[str]:
    values = []
    for cell in cells[ident_index + 1:]:
        value = clean_text(cell)
        if not value or value.upper() in {'STATUS', 'NAME', 'TICKER SYMBOL', 'EXISTING', 'NEW'}:
            continue
        values.append(value)
    return values


def parse_html_records(text: str):
    records = []
    for raw_row in HTML_ROW_RE.findall(text):
        cells = [clean_html_cell(cell) for cell in HTML_CELL_RE.findall(raw_row)]
        if not cells:
            continue
        joined = ' | '.join(cells)
        sm = SID_RE.search(joined)
        cm = CID_RE.search(joined)
        if sm and any('SERIES' in cell.upper() for cell in cells):
            sid = sm.group(1).upper()
            ident_index = next((i for i, cell in enumerate(cells) if SID_RE.search(cell)), 0)
            tail = meaningful_after_identifier(cells, ident_index)
            name = tail[0] if tail else ''
            # Ignore a duplicate identifier cell accidentally produced by nested markup.
            if SID_RE.fullmatch(name):
                name = tail[1] if len(tail) > 1 else ''
            records.append({'type': 'series', 'seriesId': sid, 'seriesName': name})
            continue
        if cm and any('CLASS/CONTRACT' in cell.upper() for cell in cells):
            cid = cm.group(1).upper()
            ident_index = next((i for i, cell in enumerate(cells) if CID_RE.search(cell)), 0)
            tail = meaningful_after_identifier(cells, ident_index)
            if tail and CID_RE.fullmatch(tail[0]):
                tail = tail[1:]
            class_name = tail[0] if tail else ''
            ticker = ''
            # Native SEC HTML has a dedicated ticker cell. Never infer ticker from the
            # final word of a class name (which produced false tickers such as PORTFOLIO).
            if len(tail) >= 2:
                candidate = tail[-1].upper()
                if candidate != 'ETF' and TICKER_RE.fullmatch(candidate):
                    ticker = candidate
            records.append({'type': 'class', 'classId': cid, 'className': class_name, 'ticker': ticker})
    return records


def parse_markdown_records(text: str):
    records = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        sm = SID_RE.search(line)
        cm = CID_RE.search(line)
        if sm and 'Series' in line:
            sid = sm.group(1).upper()
            tail = after_markdown_link(line, sid)
            # r.jina's SEC rendering places name after the linked identifier.
            # If pipe-delimited, keep the first substantive field after the id.
            fields = [clean_text(MARKDOWN_LINK_RE.sub(r'\1', x)) for x in tail.split('|')]
            fields = [x for x in fields if x]
            name = fields[0] if fields else tail
            records.append({'type': 'series', 'seriesId': sid, 'seriesName': name})
            continue
        if cm and 'Class/Contract' in line:
            cid = cm.group(1).upper()
            tail = after_markdown_link(line, cid)
            fields = [clean_text(MARKDOWN_LINK_RE.sub(r'\1', x)) for x in tail.split('|')]
            fields = [x for x in fields if x]
            ticker = ''
            class_name = ''
            if len(fields) >= 2:
                class_name = fields[0]
                candidate = fields[-1].upper()
                if candidate != 'ETF' and TICKER_RE.fullmatch(candidate):
                    ticker = candidate
            else:
                # Legacy r.jina rendering may be whitespace-only. This path is used only
                # for markdown transport, where the historical pilot was validated against
                # the frozen 2006 source filings.
                tokens = tail.split()
                candidate = tokens[-1].upper() if tokens else ''
                if candidate != 'ETF' and TICKER_RE.fullmatch(candidate):
                    ticker = candidate
                    class_name = ' '.join(tokens[:-1])
                else:
                    class_name = tail
            records.append({'type': 'class', 'classId': cid, 'className': class_name, 'ticker': ticker})
    return records


def records_to_pairs(records):
    pairs = []
    current_series = None
    for record in records:
        if record['type'] == 'series':
            current_series = record
            continue
        if record['type'] != 'class' or current_series is None:
            continue
        pairs.append({
            'seriesId': current_series['seriesId'],
            'classId': record['classId'],
            'seriesName': current_series.get('seriesName', ''),
            'className': record.get('className', ''),
            'ticker': record.get('ticker', ''),
        })
    dedup = []
    seen = set()
    for pair in pairs:
        key = (pair['seriesId'], pair['classId'], pair['ticker'], pair['seriesName'], pair['className'])
        if key not in seen:
            seen.add(key)
            dedup.append(pair)
    return dedup


def parse_pairs(text: str, transport: str):
    if transport.startswith('https://r.jina.ai/'):
        return records_to_pairs(parse_markdown_records(text))
    pairs = records_to_pairs(parse_html_records(text))
    if pairs:
        return pairs
    # Defensive fallback for SEC responses that are text-rendered rather than HTML.
    return records_to_pairs(parse_markdown_records(text))


def valid_pairs(pairs) -> bool:
    if not pairs:
        return False
    for pair in pairs:
        if not SID_RE.fullmatch(pair['seriesId']) or not CID_RE.fullmatch(pair['classId']):
            return False
        if pair['seriesName'].startswith('">') or pair['className'].startswith('">'):
            return False
    return True


def fetch_and_parse(url: str):
    attempts = []
    successful_zero = None
    # Prefer native SEC. If it is structurally unparseable or returns zero pairs,
    # use r.jina only as a transport/rendering fallback.
    for candidate in (url, 'https://r.jina.ai/' + url):
        try:
            text = fetch_one(candidate)
            pairs = parse_pairs(text, candidate)
            structurally_valid = valid_pairs(pairs)
            attempts.append({
                'transport': candidate,
                'status': 'SUCCESS',
                'pairCount': len(pairs),
                'structurallyValid': structurally_valid,
            })
            if structurally_valid:
                return pairs, candidate, attempts
            if not pairs:
                successful_zero = (pairs, candidate)
        except Exception as exc:
            attempts.append({'transport': candidate, 'status': 'ERROR', 'error': type(exc).__name__})
    if successful_zero is not None:
        pairs, candidate = successful_zero
        return pairs, candidate, attempts
    raise RuntimeError('all filing-index transports failed or were structurally invalid')


def filing_key(row):
    return (row['dateFiled'], row['cik'], row['accession'], row['form'])


def main():
    if SHARD_COUNT < 1 or not 0 <= SHARD_INDEX < SHARD_COUNT:
        raise ValueError('invalid shard configuration')
    data = json.loads(SRC.read_text())
    inventory = sorted(data['rows'], key=filing_key)
    selected = [row for i, row in enumerate(inventory) if i % SHARD_COUNT == SHARD_INDEX]
    results = []
    for row in selected:
        rec = {**row, 'pairs': []}
        try:
            pairs, transport, attempts = fetch_and_parse(row['indexUrl'])
            rec.update({
                'fetchStatus': 'SUCCESS',
                'transport': transport,
                'transportAttempts': attempts,
                'seriesClassCount': len(pairs),
                'uniqueSeriesCount': len({p['seriesId'] for p in pairs}),
                'tickerClassCount': sum(bool(p['ticker']) for p in pairs),
                'pairs': pairs,
            })
        except Exception as exc:
            rec.update({
                'fetchStatus': 'ERROR',
                'error': type(exc).__name__,
                'seriesClassCount': 0,
                'uniqueSeriesCount': 0,
                'tickerClassCount': 0,
            })
        results.append(rec)
        print('FILING', json.dumps({
            k: rec.get(k) for k in [
                'accession', 'cik', 'company', 'form', 'dateFiled', 'fetchStatus',
                'transport', 'seriesClassCount', 'uniqueSeriesCount', 'tickerClassCount', 'error'
            ]
        }), flush=True)
        time.sleep(0.04)

    successful = [r for r in results if r['fetchStatus'] == 'SUCCESS']
    with_pairs = [r for r in successful if r['seriesClassCount'] > 0]
    all_pairs = [p for r in results for p in r['pairs']]
    out = {
        'purpose': (
            'Shard of the fixed 2006-Q1 market-wide N-Q/N-Q-A inventory. Every accession is assigned '
            'by deterministic inventory position modulo SHARD_COUNT. Native SEC HTML is parsed from '
            'table-cell structure; r.jina is transport/rendering fallback. All class rows under a series '
            'are retained, including classes without tickers. Native HTML tickers are accepted only from '
            'a dedicated cell, preventing ordinary class-name words from becoming false tickers. No known '
            'Production registrants, holdings content, ranks or returns are used to select filings.'
        ),
        'inventoryArtifactId': INVENTORY_ARTIFACT_ID,
        'shardIndex': SHARD_INDEX,
        'shardCount': SHARD_COUNT,
        'fullInventoryCount': len(inventory),
        'selectedFilingCount': len(selected),
        'fetchSuccessCount': len(successful),
        'fetchErrorCount': len(results) - len(successful),
        'filingsWithSeriesClassCount': len(with_pairs),
        'parsedPairCount': len(all_pairs),
        'uniqueSeriesCount': len({p['seriesId'] for p in all_pairs}),
        'uniqueClassCount': len({p['classId'] for p in all_pairs}),
        'tickerClassCount': sum(bool(p['ticker']) for p in all_pairs),
        'uniqueTickerCount': len({p['ticker'] for p in all_pairs if p['ticker']}),
        'results': results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k != 'results'}), flush=True)


if __name__ == '__main__':
    main()
