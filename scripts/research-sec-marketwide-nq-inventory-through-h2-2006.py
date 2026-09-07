#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/research/sec-marketwide-nq-inventory-through-h2-2006.json'
UA = {
    'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research',
    'Accept': 'application/zip,text/plain,*/*',
    'Accept-Encoding': 'identity',
}
FORMS = {'N-Q', 'N-Q/A'}
CUTOFF = '2006-12-29'
MONTH_ENDS = [
    ('2006-07', '2006-07-31'),
    ('2006-08', '2006-08-31'),
    ('2006-09', '2006-09-29'),
    ('2006-10', '2006-10-31'),
    ('2006-11', '2006-11-30'),
    ('2006-12', '2006-12-29'),
]


def fetch_master(year: int, quarter: int):
    base = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}'
    zip_url = base + '/master.zip'
    req = urllib.request.Request(zip_url, headers=UA)
    with urllib.request.urlopen(req, timeout=50) as response:
        payload = response.read(25_000_000)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        member = next(name for name in archive.namelist() if name.lower().endswith('master.idx'))
        text = archive.read(member).decode('latin-1', 'replace')
    return text, zip_url, len(payload)


def accession_from_filename(filename: str):
    match = re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$', filename, re.I)
    if not match:
        return None
    return match.group(2)


def index_url(cik: str, accession: str):
    compact = accession.replace('-', '')
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{accession}-index.html'


def main():
    rows = []
    transports = {}
    master_counts = {}
    for quarter in (1, 2, 3, 4):
        text, transport, zip_bytes = fetch_master(2006, quarter)
        transports[f'2006Q{quarter}'] = {'url': transport, 'zipBytes': zip_bytes}
        master_row_count = 0
        qrows = []
        for line in text.splitlines():
            parts = line.split('|')
            if len(parts) < 5 or not parts[0].strip().isdigit():
                continue
            master_row_count += 1
            cik, company, form, date_filed, filename = [part.strip() for part in parts[:5]]
            form = form.upper()
            if form not in FORMS or date_filed > CUTOFF:
                continue
            accession = accession_from_filename(filename)
            if not accession:
                continue
            rec = {
                'cik': cik.zfill(10), 'company': company, 'form': form,
                'dateFiled': date_filed, 'filename': filename,
                'accession': accession,
                'indexUrl': index_url(cik, accession),
                'quarter': f'2006Q{quarter}',
            }
            qrows.append(rec)
        rows.extend(qrows)
        master_counts[f'2006Q{quarter}'] = master_row_count
        print('QUARTER', json.dumps({
            'quarter': quarter, 'masterRows': master_row_count,
            'nqRows': len(qrows), 'uniqueCiks': len({r['cik'] for r in qrows})
        }), flush=True)

    rows.sort(key=lambda r: (r['dateFiled'], r['cik'], r['accession'], r['form']))
    seen = set()
    dedup = []
    for row in rows:
        key = (row['accession'], row['form'])
        if key not in seen:
            seen.add(key)
            dedup.append(row)
    rows = dedup

    month_snapshots = []
    for signal_month, as_of in MONTH_ENDS:
        available = [row for row in rows if row['dateFiled'] <= as_of]
        snapshot = {
            'signalMonth': signal_month,
            'asOf': as_of,
            'filingCount': len(available),
            'uniqueRegistrantCiks': len({row['cik'] for row in available}),
            'byForm': dict(Counter(row['form'] for row in available)),
        }
        month_snapshots.append(snapshot)
        print('MONTH', json.dumps(snapshot), flush=True)

    out = {
        'purpose': (
            'Production-independent cumulative SEC source inventory through the last H2 2006 signal date. '
            'All official SEC master-index N-Q/N-Q-A filings from 2006 Q1-Q4 filed by 2006-12-29 are listed. '
            'Jul-Dec monthly snapshots are defined mechanically by filingDate <= that signal month end. No known '
            'Production registrants, legacy source accession list, holdings, ranks, returns, or strategy '
            'outcomes are used to select filings or dates.'
        ),
        'source': 'Official SEC quarterly full-index master.zip',
        'cutoff': CUTOFF,
        'quarters': [1, 2, 3, 4],
        'monthEnds': MONTH_ENDS,
        'masterRowCounts': master_counts,
        'masterTransports': transports,
        'filingCount': len(rows),
        'uniqueRegistrantCiks': len({row['cik'] for row in rows}),
        'byQuarter': dict(Counter(row['quarter'] for row in rows)),
        'byForm': dict(Counter(row['form'] for row in rows)),
        'monthSnapshots': month_snapshots,
        'rows': rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k not in ('rows', 'masterTransports', 'monthSnapshots')}), flush=True)


if __name__ == '__main__':
    main()
