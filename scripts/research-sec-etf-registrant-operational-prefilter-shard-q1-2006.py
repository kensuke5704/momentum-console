#!/usr/bin/env python3
from __future__ import annotations

import html
import io
import json
import os
import re
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/sec-marketwide-nq-inventory-q1-2006.json'
SHARD_INDEX = int(os.environ.get('SHARD_INDEX', '0'))
SHARD_COUNT = int(os.environ.get('SHARD_COUNT', '1'))
OUT = ROOT / f'data/research/sec-etf-registrant-operational-prefilter-q1-2006-shard-{SHARD_INDEX:02d}.json'
CUTOFF = '2006-03-31'
UA = {
    'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research',
    'Accept': 'text/plain,text/html,application/zip,*/*',
    'Accept-Encoding': 'identity',
}
# Annual/post-effective prospectus forms are preferred because they are most likely to
# contain the fund's operating mechanics. One recent 497 supplement is also checked.
CORE_FORMS = {'485BPOS', '485APOS', '485BXT', 'N-1A', 'N-1A/A'}
SUPPLEMENT_FORMS = {'497'}
ALL_FORMS = CORE_FORMS | SUPPLEMENT_FORMS
CREATION_PATTERNS = [
    re.compile(r'(?is)(?:offers?|issues?|sells?)\s+(?:and\s+\w+\s+)*shares?.{0,900}?creation\s+units?'),
    re.compile(r'(?is)shares?.{0,900}?(?:redeemable|redeemed|redemptions?).{0,500}?creation\s+units?'),
    re.compile(r'(?is)(?:creation\s+units?).{0,500}?(?:issued|redeemed|purchase|redemption).{0,500}?shares?'),
]
EXCHANGE_PATTERNS = [
    re.compile(r'(?is)shares?.{0,700}?(?:listed|traded).{0,300}?(?:national\s+securities\s+exchange|exchange|amex|nyse|nasdaq)'),
    re.compile(r'(?is)(?:listed|traded).{0,300}?(?:national\s+securities\s+exchange|exchange|amex|nyse|nasdaq).{0,700}?shares?'),
]
SPACE_RE = re.compile(r'\s+')


def fetch_bytes(url: str, limit: int, timeout: int = 18):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(limit), getattr(response, 'status', None)


def fetch_text(url: str, limit: int = 2_000_000, timeout: int = 18):
    errors = []
    for candidate in (url, 'https://r.jina.ai/' + url):
        try:
            payload, status = fetch_bytes(candidate, limit, timeout)
            return payload.decode('latin-1', 'replace'), candidate, status, errors
        except Exception as exc:
            errors.append({'transport': candidate, 'error': type(exc).__name__})
    raise RuntimeError(json.dumps(errors))


def get_master(year: int, quarter: int):
    base = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}'
    zip_url = base + '/master.zip'
    try:
        payload, _ = fetch_bytes(zip_url, 25_000_000, 45)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            member = next(name for name in archive.namelist() if name.lower().endswith('master.idx'))
            return archive.read(member).decode('latin-1', 'replace'), zip_url
    except Exception:
        text, transport, _, _ = fetch_text(base + '/master.idx', 25_000_000, 50)
        return text, transport


def load_prospectus_master(target_ciks: set[str]):
    by_cik = defaultdict(list)
    transports = {}
    for year, quarters in ((2005, range(1, 5)), (2006, range(1, 2))):
        for quarter in quarters:
            text, transport = get_master(year, quarter)
            transports[f'{year}Q{quarter}'] = transport
            for line in text.splitlines():
                parts = line.split('|')
                if len(parts) < 5 or not parts[0].strip().isdigit():
                    continue
                cik, company, form, date_filed, filename = [part.strip() for part in parts[:5]]
                zcik = cik.zfill(10)
                form = form.upper()
                if zcik not in target_ciks or form not in ALL_FORMS or date_filed > CUTOFF:
                    continue
                by_cik[zcik].append({
                    'cik': zcik, 'company': company, 'form': form,
                    'dateFiled': date_filed, 'filename': filename,
                })
    return by_cik, transports


def submission_url(filename: str):
    return 'https://www.sec.gov/Archives/' + filename.lstrip('/')


def find_match(patterns, text):
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match
    return None


def snippet(text: str, match, radius: int = 180):
    if not match:
        return None
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return SPACE_RE.sub(' ', html.unescape(text[start:end])).strip()


def chosen_candidates(rows):
    # Deterministic candidate policy fixed before looking at outcomes:
    # newest core prospectus + newest 497 supplement, if present.
    core = sorted((row for row in rows if row['form'] in CORE_FORMS),
                  key=lambda r: (r['dateFiled'], r['form'], r['filename']), reverse=True)
    supp = sorted((row for row in rows if row['form'] in SUPPLEMENT_FORMS),
                  key=lambda r: (r['dateFiled'], r['form'], r['filename']), reverse=True)
    chosen = []
    if core:
        chosen.append(core[0])
    if supp:
        chosen.append(supp[0])
    return chosen


def main():
    if SHARD_COUNT < 1 or not 0 <= SHARD_INDEX < SHARD_COUNT:
        raise ValueError('invalid shard configuration')
    inventory = json.loads(SRC.read_text())
    filings = inventory['rows']
    by_cik_nq = defaultdict(list)
    for row in filings:
        by_cik_nq[row['cik']].append(row)
    all_ciks = sorted(by_cik_nq)
    selected_ciks = [cik for index, cik in enumerate(all_ciks) if index % SHARD_COUNT == SHARD_INDEX]
    prospectus_by_cik, master_transports = load_prospectus_master(set(selected_ciks))

    results = []
    for cik in selected_ciks:
        nq_rows = sorted(by_cik_nq[cik], key=lambda r: (r['dateFiled'], r['accession']))
        prospectus_rows = prospectus_by_cik.get(cik, [])
        candidates = chosen_candidates(prospectus_rows)
        rec = {
            'cik': cik,
            'companyNames': sorted({row['company'] for row in nq_rows}),
            'nqFilingCount': len(nq_rows),
            'nqFirstDate': nq_rows[0]['dateFiled'],
            'nqLastDate': nq_rows[-1]['dateFiled'],
            'prospectusCandidatePoolCount': len(prospectus_rows),
            'checkedCandidateCount': len(candidates),
            'candidateRegistrant': False,
            'attempts': [],
        }
        for filing in candidates:
            attempt = {k: filing[k] for k in ('form', 'dateFiled', 'filename')}
            url = submission_url(filing['filename'])
            try:
                text, transport, status, prior = fetch_text(url, 2_000_000, 18)
                creation = find_match(CREATION_PATTERNS, text)
                exchange = find_match(EXCHANGE_PATTERNS, text)
                attempt.update({
                    'submissionUrl': url,
                    'transport': transport,
                    'httpStatus': status,
                    'priorTransportErrors': prior,
                    'creationOperationalEvidence': bool(creation),
                    'exchangeTradingEvidence': bool(exchange),
                    'jointOperationalEvidence': bool(creation and exchange),
                    'creationSnippet': snippet(text, creation),
                    'exchangeSnippet': snippet(text, exchange),
                })
                if creation and exchange:
                    rec['candidateRegistrant'] = True
                    rec['positiveEvidence'] = {
                        'form': filing['form'], 'dateFiled': filing['dateFiled'],
                        'filename': filing['filename'], 'submissionUrl': url,
                        'creationSnippet': attempt['creationSnippet'],
                        'exchangeSnippet': attempt['exchangeSnippet'],
                    }
            except Exception as exc:
                attempt.update({'submissionUrl': url, 'error': type(exc).__name__})
            rec['attempts'].append(attempt)
            if rec['candidateRegistrant']:
                break
            time.sleep(0.03)
        results.append(rec)
        print('REGISTRANT', json.dumps({
            key: rec.get(key) for key in (
                'cik', 'companyNames', 'nqFilingCount', 'prospectusCandidatePoolCount',
                'checkedCandidateCount', 'candidateRegistrant'
            )
        }), flush=True)

    positives = [row for row in results if row['candidateRegistrant']]
    out = {
        'purpose': (
            'Loss-minimizing candidate prefilter over every registrant CIK in the fixed 2006-Q1 market-wide '
            'N-Q/N-Q-A inventory. It is NOT a final ETF classification. For each registrant, the deterministic '
            'newest core prospectus and newest 497 supplement filed by 2006-03-31 are inspected for the same '
            'Creation Unit plus exchange-listing/trading operational conjunction validated in the separate ETF '
            'pilot. Positive CIKs proceed to series-level PIT validation; negative CIKs are not yet excluded '
            'from the final source population until prefilter recall is separately checked. No Production source '
            'list, holdings outcomes, ranks, returns, or strategy results are used.'
        ),
        'inventoryArtifactId': 9945162305,
        'cutoff': CUTOFF,
        'shardIndex': SHARD_INDEX,
        'shardCount': SHARD_COUNT,
        'fullRegistrantCount': len(all_ciks),
        'selectedRegistrantCount': len(selected_ciks),
        'registrantsWithProspectusCandidates': sum(bool(prospectus_by_cik.get(cik)) for cik in selected_ciks),
        'positiveCandidateRegistrantCount': len(positives),
        'positiveCiks': [row['cik'] for row in positives],
        'masterTransports': master_transports,
        'results': results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k not in ('results', 'masterTransports')}), flush=True)


if __name__ == '__main__':
    main()
