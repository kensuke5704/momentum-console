#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT = ROOT / 'data/research/country-cik-only-header-diagnostic-v29.json'
UA = {'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research', 'Accept': 'text/plain,text/html,*/*', 'Accept-Encoding': 'identity'}
US_CODES = {'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
SAMPLE_N = 240
CACHE = {}


def fetch(url: str) -> tuple[str, str]:
    if url in CACHE:
        return CACHE[url]
    last = None
    for candidate in ('https://r.jina.ai/' + url, url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=18) as r:
                text = r.read(400_000).decode('latin-1', 'replace')
            CACHE[url] = (text, candidate)
            return CACHE[url]
        except Exception as exc:
            last = exc
    raise RuntimeError(type(last).__name__ if last else 'fetch failed')


def cik_state(cik: str, text: str) -> tuple[str | None, str | None]:
    zcik = str(cik).zfill(10)
    cleaned = html.unescape(re.sub(r'<[^>]*>', '', text)).replace('\r', '')
    states = []

    # Flat SEC-HEADER grammar. Identity has already been established upstream by
    # historical exact issuer-form -> unique CIK, so the CIK itself is the entity key.
    for block in re.split(r'(?im)^\s*COMPANY\s+DATA\s*:\s*$', cleaned)[1:]:
        part = re.split(r'(?im)^\s*(?:FILING\s+VALUES|BUSINESS\s+ADDRESS|MAIL\s+ADDRESS|FORMER\s+COMPANY)\s*:\s*$', block, maxsplit=1)[0]
        ck = re.search(r'(?im)^\s*CENTRAL\s+INDEX\s+KEY\s*:\s*(\d{1,10})\s*$', part)
        st = re.search(r'(?im)^\s*STATE\s+OF\s+INCORPORATION\s*:\s*([A-Z0-9]{2,3})\s*$', part)
        if ck and ck.group(1).zfill(10) == zcik and st:
            states.append(st.group(1).upper())

    # SGML header grammar.
    for block in re.findall(r'<COMPANY-DATA>(.*?)(?=</COMPANY-DATA>|<FILING-VALUES>|<BUSINESS-ADDRESS>|<MAIL-ADDRESS>|<FORMER-COMPANY>|</FILER>|</ISSUER>|$)', text, flags=re.I | re.S):
        ck = re.search(r'<CIK>\s*(\d{1,10})', block, re.I)
        st = re.search(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})', block, re.I)
        if ck and ck.group(1).zfill(10) == zcik and st:
            states.append(st.group(1).upper())

    # Rendered-text fallback: accept only an explicit STATE OF INCORPORATION label
    # within a bounded neighborhood of the same historical CIK, and only when unique.
    for m in re.finditer(r'(?i)(?:CENTRAL\s+INDEX\s+KEY|CIK)\s*[:#]?\s*0*(\d{1,10})', cleaned):
        if m.group(1).zfill(10) != zcik:
            continue
        lo = max(0, m.start() - 1800)
        hi = min(len(cleaned), m.end() + 1800)
        window = cleaned[lo:hi]
        for st in re.findall(r'(?i)STATE\s+OF\s+INCORPORATION\s*[:\-]?\s*([A-Z0-9]{2,3})\b', window):
            states.append(st.upper())

    uniq = sorted(set(states))
    if len(uniq) == 1:
        return uniq[0], 'CIK_BOUND_STATE_OF_INCORPORATION'
    return None, None


def row_seed(row: dict):
    seeds = set()
    filings = []
    for attempt in row.get('attempts', []):
        if attempt.get('historicalExactCikCount') == 1 and attempt.get('seedCik'):
            seeds.add(str(attempt['seedCik']).zfill(10))
            for filing in attempt.get('filingAttempts', []):
                if filing.get('submissionUrl') and filing.get('dateFiled') and filing.get('dateFiled') <= row.get('asOfReportDate', ''):
                    filings.append(filing)
    if len(seeds) != 1:
        return None, []
    seen = set(); ordered = []
    for f in filings:
        u = f['submissionUrl']
        if u not in seen:
            seen.add(u); ordered.append(f)
    return next(iter(seeds)), ordered[:6]


def main():
    data = json.loads(SRC.read_text())
    unknown = [r for r in data.get('resolutionAudit', []) if r.get('classification') == 'UNKNOWN']
    eligible = []
    for row in unknown:
        seed, filings = row_seed(row)
        if seed and filings:
            eligible.append((row, seed, filings))
    eligible.sort(key=lambda x: ((x[0].get('ticker') or ''), (x[0].get('securityId') or ''), x[0].get('asOfReportDate') or ''))
    n = min(SAMPLE_N, len(eligible))
    positions = sorted(set(min(len(eligible)-1, (i * len(eligible)) // n) for i in range(n))) if n else []
    sample = [eligible[i] for i in positions]

    results = []
    for row, seed, filings in sample:
        rec = {'ticker': row.get('ticker'), 'securityId': row.get('securityId'), 'asOfReportDate': row.get('asOfReportDate'), 'seedCik': seed, 'classification': 'UNKNOWN', 'attempts': []}
        states = []
        for filing in filings:
            try:
                text, transport = fetch(filing['submissionUrl'])
                state, method = cik_state(seed, text)
                rec['attempts'].append({'form': filing.get('form'), 'dateFiled': filing.get('dateFiled'), 'submissionUrl': filing.get('submissionUrl'), 'transport': transport, 'stateCode': state, 'method': method})
                if state:
                    states.append(state)
            except Exception as exc:
                rec['attempts'].append({'form': filing.get('form'), 'dateFiled': filing.get('dateFiled'), 'submissionUrl': filing.get('submissionUrl'), 'error': type(exc).__name__})
        uniq = sorted(set(states))
        if len(uniq) == 1:
            rec['stateCode'] = uniq[0]
            rec['classification'] = 'US' if uniq[0] in US_CODES else 'NON_US'
            rec['resolutionSource'] = 'PIT_HISTORICAL_UNIQUE_CIK_HEADER_STATE'
        elif len(uniq) > 1:
            rec['conflictStates'] = uniq
        results.append(rec)

    resolved = [r for r in results if r['classification'] != 'UNKNOWN']
    out = {
        'purpose': 'Return-independent diagnostic of whether a historical exact issuer-form -> unique CIK seed can be followed by a pre-report-date SEC submission header STATE OF INCORPORATION using the CIK as the entity key. No current ticker metadata, fuzzy matching, US default, universe ranks, returns or strategy outcomes are used.',
        'inputUnknownCount': len(unknown),
        'eligibleUniqueCikWithHistoricalFilingCount': len(eligible),
        'sampleRule': f'{SAMPLE_N} equal-quantile positions after deterministic ticker/securityId/reportDate sort',
        'sampleCount': len(results),
        'resolvedCount': len(resolved),
        'resolvedUSCount': sum(r['classification'] == 'US' for r in resolved),
        'resolvedNonUSCount': sum(r['classification'] == 'NON_US' for r in resolved),
        'conflictCount': sum(bool(r.get('conflictStates')) for r in results),
        'fetchCacheCount': len(CACHE),
        'results': results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k:v for k,v in out.items() if k != 'results'}), flush=True)


if __name__ == '__main__':
    main()
