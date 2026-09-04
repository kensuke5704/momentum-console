#!/usr/bin/env python3
from __future__ import annotations

import html
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/research/sec-historical-etf-operational-evidence-pilot-2006.json'
UA = {
    'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research',
    'Accept': 'text/plain,text/html,application/zip,*/*',
    'Accept-Encoding': 'identity',
}
PROSPECTUS_FORMS = {
    '485APOS', '485BPOS', '485BXT', '485A24F', '497', 'N-1A', 'N-1A/A'
}
SAMPLES = [
    {
        'label': 'SELECT_SECTOR_XLY', 'expectedType': 'KNOWN_ETF_VALIDATION',
        'cik': '0001064641', 'nqDate': '2006-02-28', 'seriesId': 'S000006408',
        'seriesName': 'Consumer Discretionary Select Sector SPDR Fund',
    },
    {
        'label': 'RYDEX_XLG', 'expectedType': 'KNOWN_ETF_VALIDATION',
        'cik': '0001208211', 'nqDate': '2006-03-27', 'seriesId': 'S000010907',
        'seriesName': 'Russell Top 50 ETF',
    },
    {
        'label': 'DREYFUS_GNMA', 'expectedType': 'CONVENTIONAL_FUND_COMPARISON',
        'cik': '0000762156', 'nqDate': '2006-03-16', 'seriesId': 'S000000069',
        'seriesName': 'Dreyfus GNMA Fund',
    },
    {
        'label': 'TROWE_US_BOND_INDEX', 'expectedType': 'CONVENTIONAL_FUND_COMPARISON',
        'cik': '0001120924', 'nqDate': '2006-03-28', 'seriesId': 'S000002166',
        'seriesName': 'T. Rowe Price U.S. Bond Index Fund',
    },
    {
        'label': 'AIC_STERLING_SMALL_CAP', 'expectedType': 'CONVENTIONAL_FUND_COMPARISON',
        'cik': '0000935069', 'nqDate': '2006-03-23', 'seriesId': 'S000005710',
        'seriesName': 'Sterling Capital Small Cap Value Fund',
    },
]
SID_RE = re.compile(r'\bS\d{9}\b', re.I)
SPACE_RE = re.compile(r'\s+')
CREATION_PATTERNS = [
    re.compile(r'(?is)(?:offers?|issues?|sells?)\s+(?:and\s+\w+\s+)*shares?.{0,900}?creation\s+units?'),
    re.compile(r'(?is)shares?.{0,900}?(?:redeemable|redeemed|redemptions?).{0,500}?creation\s+units?'),
    re.compile(r'(?is)(?:creation\s+units?).{0,500}?(?:issued|redeemed|purchase|redemption).{0,500}?shares?'),
]
EXCHANGE_PATTERNS = [
    re.compile(r'(?is)shares?.{0,700}?(?:listed|traded).{0,300}?(?:national\s+securities\s+exchange|exchange|amex|nyse|nasdaq)'),
    re.compile(r'(?is)(?:listed|traded).{0,300}?(?:national\s+securities\s+exchange|exchange|amex|nyse|nasdaq).{0,700}?shares?'),
]


def fetch_bytes(url: str, limit: int, timeout: int = 35):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(limit), getattr(response, 'status', None)


def fetch_text(url: str, limit: int = 1_500_000, timeout: int = 18):
    errors = []
    for candidate in (url, 'https://r.jina.ai/' + url):
        try:
            payload, status = fetch_bytes(candidate, limit, timeout)
            return payload.decode('utf-8', 'replace'), candidate, status, errors
        except Exception as exc:
            errors.append({'transport': candidate, 'error': type(exc).__name__})
    raise RuntimeError(json.dumps(errors))


def get_master(year: int, quarter: int):
    base = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}'
    zip_url = base + '/master.zip'
    try:
        payload, _ = fetch_bytes(zip_url, 25_000_000, 50)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            member = next(name for name in archive.namelist() if name.lower().endswith('master.idx'))
            return archive.read(member).decode('latin-1', 'replace'), zip_url
    except Exception:
        text, transport, _, _ = fetch_text(base + '/master.idx', 25_000_000, 50)
        return text, transport


def load_master():
    rows = []
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
                if form.upper() not in PROSPECTUS_FORMS:
                    continue
                rows.append({
                    'cik': cik.zfill(10), 'company': company, 'form': form.upper(),
                    'dateFiled': date_filed, 'filename': filename,
                })
    return rows, transports


def accession_parts(filename: str):
    match = re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$', filename, re.I)
    if not match:
        return None
    archive_cik = str(int(match.group(1)))
    accession = match.group(2)
    return archive_cik, accession, accession.replace('-', '')


def index_url(filename: str):
    parts = accession_parts(filename)
    if not parts:
        return None
    cik, accession, compact = parts
    return f'https://www.sec.gov/Archives/edgar/data/{cik}/{compact}/{accession}-index.html'


def submission_url(filename: str):
    return 'https://www.sec.gov/Archives/' + filename.lstrip('/')


def normalize(value: str) -> str:
    value = html.unescape(value or '').upper()
    value = re.sub(r'[^A-Z0-9]+', ' ', value)
    return ' '.join(value.split())


def operational_matches(text: str):
    creation = next((pattern.search(text) for pattern in CREATION_PATTERNS if pattern.search(text)), None)
    exchange = next((pattern.search(text) for pattern in EXCHANGE_PATTERNS if pattern.search(text)), None)
    return creation, exchange


def snippet(text: str, match, radius: int = 220):
    if not match:
        return None
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return SPACE_RE.sub(' ', html.unescape(text[start:end])).strip()


def evidence_for(sample, master_rows):
    candidates = [
        row for row in master_rows
        if row['cik'] == sample['cik'] and row['dateFiled'] <= sample['nqDate']
    ]
    candidates.sort(key=lambda row: (row['dateFiled'], row['form'], row['filename']), reverse=True)
    rec = {**sample, 'candidateCount': len(candidates), 'attempts': [], 'classification': 'UNKNOWN'}
    target_name = normalize(sample['seriesName'])
    for filing in candidates[:16]:
        attempt = {k: filing[k] for k in ('form', 'dateFiled', 'filename')}
        iu = index_url(filing['filename'])
        try:
            index_text, index_transport, _, index_errors = fetch_text(iu, 700_000, 14)
            series_ids = sorted({match.upper() for match in SID_RE.findall(index_text)})
            series_id_bound = sample['seriesId'] in series_ids
            attempt.update({
                'indexUrl': iu, 'indexTransport': index_transport,
                'indexPriorErrors': index_errors, 'seriesIdCount': len(series_ids),
                'seriesIdBound': series_id_bound,
            })
        except Exception as exc:
            attempt.update({'indexUrl': iu, 'indexError': type(exc).__name__})
            series_id_bound = False
        try:
            su = submission_url(filing['filename'])
            payload, status = fetch_bytes(su, 4_000_000, 22)
            text = payload.decode('latin-1', 'replace')
            creation, exchange = operational_matches(text)
            normalized_submission = normalize(text[:4_000_000])
            series_name_bound = bool(target_name and target_name in normalized_submission)
            bound = series_id_bound or series_name_bound
            attempt.update({
                'submissionUrl': su, 'submissionHttpStatus': status,
                'bytesRead': len(payload), 'seriesNameBound': series_name_bound,
                'creationOperationalEvidence': bool(creation),
                'exchangeTradingEvidence': bool(exchange),
                'creationSnippet': snippet(text, creation),
                'exchangeSnippet': snippet(text, exchange),
                'seriesBoundOperationalEtfEvidence': bool(bound and creation and exchange),
            })
            rec['attempts'].append(attempt)
            if bound and creation and exchange:
                rec.update({
                    'classification': 'ETF_OPERATIONAL_EVIDENCE',
                    'evidenceForm': filing['form'], 'evidenceDateFiled': filing['dateFiled'],
                    'evidenceFilename': filing['filename'],
                    'seriesBinding': 'SERIES_ID' if series_id_bound else 'SERIES_NAME',
                    'creationSnippet': attempt['creationSnippet'],
                    'exchangeSnippet': attempt['exchangeSnippet'],
                })
                return rec
        except Exception as exc:
            attempt.update({'submissionError': type(exc).__name__})
            rec['attempts'].append(attempt)
    return rec


def main():
    master_rows, transports = load_master()
    results = []
    for sample in SAMPLES:
        rec = evidence_for(sample, master_rows)
        results.append(rec)
        print('ETF_EVIDENCE', json.dumps({
            key: rec.get(key) for key in (
                'label', 'expectedType', 'seriesId', 'classification', 'evidenceForm',
                'evidenceDateFiled', 'seriesBinding', 'candidateCount'
            )
        }), flush=True)
    out = {
        'purpose': (
            'Pre-registered structural pilot for historical ETF source eligibility. A series is positive '
            'only when a pre-N-Q SEC prospectus/registration filing can be bound to the target series by '
            'historical Series ID or normalized series name and the same filing contains both operational '
            'Creation Unit issuance/redemption language and operational exchange listing/trading language. '
            'The literal token ETF is not required. Known ETF and conventional-fund labels are validation '
            'only; no returns, ranks, holdings outcomes, or Production source list are used to tune the rule.'
        ),
        'masterTransports': transports,
        'prospectusForms': sorted(PROSPECTUS_FORMS),
        'sampleCount': len(results),
        'positiveCount': sum(r['classification'] == 'ETF_OPERATIONAL_EVIDENCE' for r in results),
        'results': results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k not in ('results', 'masterTransports')}), flush=True)


if __name__ == '__main__':
    main()
