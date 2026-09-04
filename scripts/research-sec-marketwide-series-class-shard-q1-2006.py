#!/usr/bin/env python3
from __future__ import annotations

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
UA = {
    'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research',
    'Accept': 'text/html,text/plain,*/*',
    'Accept-Encoding': 'identity',
}
SID_RE = re.compile(r'\b(S\d{9})\b', re.I)
CID_RE = re.compile(r'\b(C\d{9})\b', re.I)
TICKER_RE = re.compile(r'^[A-Z][A-Z0-9.\-]{0,9}$')


def fetch(url: str, timeout: int = 18):
    errors = []
    for candidate in (url, 'https://r.jina.ai/' + url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = response.read(1_500_000)
            return payload.decode('utf-8', 'replace'), candidate, errors
        except Exception as exc:
            errors.append({'transport': candidate, 'error': type(exc).__name__})
    raise RuntimeError(json.dumps(errors))


def after_markdown_link(line: str, ident: str):
    match = re.search(rf'\[{re.escape(ident)}\]\([^\)]+\)(.*)$', line, re.I)
    if match:
        return ' '.join(match.group(1).split())
    pos = line.upper().find(ident.upper())
    if pos >= 0:
        return ' '.join(line[pos + len(ident):].lstrip(' ]()').split())
    return ''


def parse_pairs(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pairs = []
    for index, line in enumerate(lines):
        if 'Series' not in line:
            continue
        sm = SID_RE.search(line)
        if not sm:
            continue
        sid = sm.group(1).upper()
        series_name = after_markdown_link(line, sid)
        # SEC rendered filing-index output places Class/Contract immediately after Series.
        # Keep class rows even if a ticker was not assigned historically.
        for nxt in lines[index + 1:index + 6]:
            if 'Series' in nxt and SID_RE.search(nxt):
                break
            if 'Class/Contract' not in nxt:
                continue
            cm = CID_RE.search(nxt)
            if not cm:
                continue
            cid = cm.group(1).upper()
            tail = after_markdown_link(nxt, cid)
            tokens = tail.split()
            ticker = ''
            class_name = tail
            if tokens:
                token = tokens[-1].upper()
                # Some inactive historical classes render a literal placeholder `ETF`.
                if token != 'ETF' and TICKER_RE.fullmatch(token):
                    ticker = token
                    class_name = ' '.join(tokens[:-1])
            pairs.append({
                'seriesId': sid,
                'classId': cid,
                'seriesName': series_name,
                'className': class_name,
                'ticker': ticker,
            })
            break

    dedup = []
    seen = set()
    for pair in pairs:
        key = (pair['seriesId'], pair['classId'], pair['ticker'], pair['seriesName'], pair['className'])
        if key not in seen:
            seen.add(key)
            dedup.append(pair)
    return dedup


def filing_key(row):
    return (row['dateFiled'], row['cik'], row['accession'], row['form'])


def main():
    if SHARD_COUNT < 1 or not 0 <= SHARD_INDEX < SHARD_COUNT:
        raise ValueError('invalid shard configuration')
    data = json.loads(SRC.read_text())
    inventory = sorted(data['rows'], key=filing_key)
    selected = [row for i, row in enumerate(inventory) if i % SHARD_COUNT == SHARD_INDEX]
    results = []
    for i, row in enumerate(selected, 1):
        rec = {**row, 'pairs': []}
        try:
            text, transport, prior_errors = fetch(row['indexUrl'])
            pairs = parse_pairs(text)
            rec.update({
                'fetchStatus': 'SUCCESS',
                'transport': transport,
                'priorTransportErrors': prior_errors,
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
            'by deterministic inventory position modulo SHARD_COUNT. Filing-index Series/Class metadata '
            'is parsed without using known Production registrants, holdings content, ranks or returns. '
            'Classes without tickers are retained; literal placeholder ETF is treated as no ticker.'
        ),
        'inventoryArtifactId': None,
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
