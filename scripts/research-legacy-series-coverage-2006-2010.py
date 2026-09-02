#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com', 'Accept': '*/*'}
OUT = ROOT / 'data' / 'research' / 'legacy-series-coverage-2006-2010.json'
YEARS = range(2006, 2011)
TARGET_HINTS = (
    'ISHARES', 'SELECT SECTOR SPDR', 'STREETTRACKS', 'SPDR', 'POWERSHARES', 'INVESCO',
    'RYDEX ETF', 'PROSHARES', 'VANGUARD', 'ETF TRUST', 'ETF SERIES', 'EXCHANGE-TRADED'
)

spec = importlib.util.spec_from_file_location('meta', ROOT / 'scripts' / 'research-nq-series-metadata-2006.py')
meta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(meta)


def download(path: Path) -> None:
    req = urllib.request.Request(DRIVE, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
        while True:
            b = r.read(1024 * 1024)
            if not b:
                break
            f.write(b)


def hinted(company: str) -> bool:
    u = company.upper()
    return any(x in u for x in TARGET_HINTS)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / 'master.zip'
        download(zp)
        filings_by_year = defaultdict(list)
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
                        if form.upper() != 'N-Q' or not date_filed.startswith(str(year)) or not hinted(company):
                            continue
                        filings_by_year[year].append({'cik': cik, 'company': company, 'dateFiled': date_filed, 'filename': filename})

    results = []
    for year in YEARS:
        rows = sorted(filings_by_year[year], key=lambda r: (r['dateFiled'], r['cik'], r['filename']))
        chosen = []
        seen = set()
        for row in rows:
            if row['cik'] in seen:
                continue
            seen.add(row['cik'])
            chosen.append(row)
            if len(chosen) >= 12:
                break

        for i, row in enumerate(chosen, 1):
            try:
                method, text = meta.fetch_prefix(meta.sec_url(row['filename']))
                series = meta.parse_series_contracts(text, row['company'])
                etf = [s for s in series if s.get('isEtf')]
                tickers = sorted({t for s in etf for t in s.get('etfTickers', [])})
                rec = {
                    'year': year,
                    'cik': row['cik'],
                    'company': row['company'],
                    'filingDate': row['dateFiled'],
                    'transport': method,
                    'seriesBlockCount': len(series),
                    'classifiedEtfSeries': len(etf),
                    'classifiedEtfTickerCount': len(tickers),
                    'sampleTickers': tickers[:30],
                }
                print(f"{year} {i}/{len(chosen)} {row['company'][:42]} series={len(series)} etf={len(etf)} tickers={len(tickers)}", flush=True)
            except Exception as e:
                rec = {'year': year, 'cik': row['cik'], 'company': row['company'], 'filingDate': row['dateFiled'], 'error': repr(e)}
                print(f"{year} {i}/{len(chosen)} FAIL {row['company'][:42]} {e!r}", flush=True)
            results.append(rec)
            time.sleep(1.0)

    by_year = {}
    for year in YEARS:
        r = [x for x in results if x['year'] == year]
        ok = [x for x in r if 'error' not in x]
        by_year[str(year)] = {
            'sampledRegistrants': len(r),
            'fetchSucceeded': len(ok),
            'withStructuredSeries': sum(x.get('seriesBlockCount', 0) > 0 for x in ok),
            'withClassifiedEtfSeries': sum(x.get('classifiedEtfSeries', 0) > 0 for x in ok),
            'withEtfTickerMetadata': sum(x.get('classifiedEtfTickerCount', 0) > 0 for x in ok),
        }

    out = {
        'purpose': 'Development-window structural coverage probe for legacy ETF series metadata. No price, return, strategy, or performance data used.',
        'performanceWindowPolicy': 'This script only inspects filing structure in 2006-2010 and does not open any performance history.',
        'sampleRule': 'Up to 12 distinct ETF-family-hint CIKs per year, first N-Q filing in deterministic filing-date/CIK order; no parser-success or performance selection.',
        'byYear': by_year,
        'results': results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k != 'results'}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
