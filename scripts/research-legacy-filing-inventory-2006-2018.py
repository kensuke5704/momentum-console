#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com', 'Accept': '*/*'}
OUT = ROOT / 'data' / 'research' / 'legacy-filing-inventory-2006-2018.json'
YEARS = range(2006, 2019)
FORMS = {'N-Q', 'N-Q/A', 'N-CSR', 'N-CSRS', 'N-CSR/A', 'N-CSRS/A', 'N-PX', 'N-PX/A'}
ETF_FAMILY_HINTS = (
    'ISHARES', 'SELECT SECTOR SPDR', 'STREETTRACKS', 'SPDR', 'POWERSHARES', 'INVESCO',
    'RYDEX ETF', 'PROSHARES', 'VANGUARD', 'ETF TRUST', 'ETF SERIES', 'EXCHANGE-TRADED'
)


def download(path: Path) -> None:
    req = urllib.request.Request(DRIVE, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
        while True:
            b = r.read(1024 * 1024)
            if not b:
                break
            f.write(b)


def looks_etf_family(company: str) -> bool:
    u = company.upper()
    return any(x in u for x in ETF_FAMILY_HINTS)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / 'master.zip'
        download(zp)
        rows = []
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            for year in YEARS:
                qfiles = [n for n in names if any(f'master_{year}_QTR{q}.idx' in n for q in range(1, 5))]
                for name in sorted(qfiles):
                    text = z.read(name).decode('latin-1', 'replace')
                    for line in text.splitlines():
                        p = line.split('|')
                        if len(p) < 5:
                            continue
                        cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
                        form = form.upper()
                        if form not in FORMS or not date_filed.startswith(str(year)):
                            continue
                        rows.append({
                            'year': year,
                            'month': date_filed[:7],
                            'cik': cik,
                            'company': company,
                            'form': form,
                            'dateFiled': date_filed,
                            'filename': filename,
                            'etfFamilyHint': looks_etf_family(company),
                        })

    by_year = {}
    for year in YEARS:
        yr = [r for r in rows if r['year'] == year]
        form_counts = defaultdict(int)
        month_counts = defaultdict(int)
        etf_form_counts = defaultdict(int)
        unique_ciks = set()
        etf_ciks = set()
        for r in yr:
            form_counts[r['form']] += 1
            month_counts[r['month']] += 1
            unique_ciks.add(r['cik'])
            if r['etfFamilyHint']:
                etf_form_counts[r['form']] += 1
                etf_ciks.add(r['cik'])
        by_year[str(year)] = {
            'filings': len(yr),
            'uniqueRegistrantCiks': len(unique_ciks),
            'formCounts': dict(sorted(form_counts.items())),
            'monthCounts': dict(sorted(month_counts.items())),
            'etfFamilyHintRegistrantCiks': len(etf_ciks),
            'etfFamilyHintFormCounts': dict(sorted(etf_form_counts.items())),
        }

    # Persist only structural 2018 ETF-family filing rows so later continuity
    # analysis does not need to download the large historical master index again.
    # This contains no holdings, prices, returns, ranks, or strategy outcomes.
    continuity_rows_2018 = [
        {k: r[k] for k in ('cik', 'company', 'form', 'dateFiled', 'filename')}
        for r in rows
        if r['year'] == 2018 and r['etfFamilyHint']
    ]
    continuity_rows_2018.sort(key=lambda r: (r['dateFiled'], r['cik'], r['form'], r['filename']))

    out = {
        'purpose': 'Structural filing-availability inventory for legacy ETF universe reconstruction. No prices, returns, strategy outputs, or performance metrics are accessed.',
        'years': [2006, 2018],
        'forms': sorted(FORMS),
        'etfFamilyHintRule': list(ETF_FAMILY_HINTS),
        'totalTargetFilings': len(rows),
        'byYear': by_year,
        'continuityRows2018': continuity_rows_2018,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k != 'continuityRows2018'}, sort_keys=True), flush=True)
    print('CONTINUITY_ROWS_2018', len(continuity_rows_2018), flush=True)


if __name__ == '__main__':
    main()
