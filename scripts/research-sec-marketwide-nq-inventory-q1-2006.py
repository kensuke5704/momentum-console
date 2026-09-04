#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/research/sec-marketwide-nq-inventory-q1-2006.json'
YEAR = 2006
QUARTER = 1
FORMS = {'N-Q', 'N-Q/A'}
UA = {
    'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research',
    'Accept': 'text/plain,application/zip,*/*',
    'Accept-Encoding': 'identity',
}


def fetch_text(url: str, timeout: int = 60):
    last = None
    for candidate in (url, 'https://r.jina.ai/' + url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('latin-1', 'replace'), candidate
        except Exception as exc:
            last = f'{type(exc).__name__}: {exc}'
    raise RuntimeError(last or 'fetch failed')


def fetch_master(year: int, quarter: int):
    base = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}'
    zip_url = base + '/master.zip'
    try:
        req = urllib.request.Request(zip_url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = response.read(30_000_000)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            name = next(n for n in archive.namelist() if n.lower().endswith('master.idx'))
            return archive.read(name).decode('latin-1', 'replace'), zip_url, None
    except Exception as exc:
        text, transport = fetch_text(base + '/master.idx', timeout=60)
        return text, transport, type(exc).__name__


def accession_from_filename(filename: str):
    m = re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$', filename, re.I)
    if not m:
        return None
    cik = str(int(m.group(1)))
    accession = m.group(2)
    return cik, accession


def main():
    text, transport, zip_error = fetch_master(YEAR, QUARTER)
    rows = []
    total_master_rows = 0
    for line in text.splitlines():
        parts = line.split('|')
        if len(parts) < 5 or not parts[0].strip().isdigit():
            continue
        cik, company, form, date_filed, filename = [x.strip() for x in parts[:5]]
        total_master_rows += 1
        form = form.upper()
        if form not in FORMS:
            continue
        accession_parts = accession_from_filename(filename)
        if not accession_parts:
            continue
        archive_cik, accession = accession_parts
        compact = accession.replace('-', '')
        rows.append({
            'cik': cik.zfill(10),
            'archiveCik': archive_cik,
            'company': company,
            'form': form,
            'dateFiled': date_filed,
            'filename': filename,
            'accession': accession,
            'indexUrl': (
                f'https://www.sec.gov/Archives/edgar/data/{archive_cik}/'
                f'{compact}/{accession}-index.html'
            ),
        })

    rows.sort(key=lambda r: (r['dateFiled'], r['cik'], r['accession'], r['form']))
    unique_accessions = sorted({r['accession'] for r in rows})
    unique_ciks = sorted({r['cik'] for r in rows})
    out = {
        'purpose': (
            'Market-wide Production-independent source acquisition for the fixed calendar quarter '
            '2006 Q1. Enumerate every SEC master-index N-Q/N-Q-A filing before any Series/Class, '
            'holdings, ticker, rank, return, or Production-Universe inspection. No known source '
            'registrant/accession is used to seed or filter this inventory.'
        ),
        'year': YEAR,
        'quarter': QUARTER,
        'forms': sorted(FORMS),
        'masterTransport': transport,
        'masterZipFallbackError': zip_error,
        'masterParsedRowCount': total_master_rows,
        'nqRowCount': len(rows),
        'uniqueAccessionCount': len(unique_accessions),
        'uniqueRegistrantCikCount': len(unique_ciks),
        'rows': rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k != 'rows'}), flush=True)
    for row in rows[:25]:
        print('NQ', json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
