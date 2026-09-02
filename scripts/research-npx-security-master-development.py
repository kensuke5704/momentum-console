#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com', 'Accept': '*/*'}
OUT = ROOT / 'data' / 'research' / 'npx-security-master-development.json'
YEARS = (2006, 2008, 2010)
SAMPLE_PER_YEAR = 32

spec = importlib.util.spec_from_file_location('pilot', ROOT / 'scripts' / 'research-npx-security-master-2006.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def normalize_issuer(raw: str) -> str:
    s = raw.upper().replace('&', ' AND ')
    s = re.sub(r'\b(INCORPORATED|INCORPORATION)\b', 'INC', s)
    s = re.sub(r'\bCORPORATION\b', 'CORP', s)
    s = re.sub(r'\bCOMPANY\b', 'CO', s)
    s = re.sub(r'\bLIMITED\b', 'LTD', s)
    return ' '.join(re.sub(r'[^A-Z0-9]+', ' ', s).split())


def quantile_sample(rows: list[dict], n: int) -> list[dict]:
    rows = [r for r in rows if r['form'] == 'N-PX']
    if len(rows) <= n:
        return rows
    positions = sorted(set(round(i * (len(rows) - 1) / (n - 1)) for i in range(n)))
    return [rows[p] for p in positions]


def filing_indexes() -> dict[int, list[dict]]:
    by_year = defaultdict(list)
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / 'master.zip'
        pilot.download(DRIVE, zp)
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            for year in YEARS:
                qfiles = sorted(n for n in names if re.search(rf'master_{year}_QTR[1-4]\.idx$', n))
                for name in qfiles:
                    for line in z.read(name).decode('latin-1', 'replace').splitlines():
                        p = line.split('|')
                        if len(p) < 5:
                            continue
                        cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
                        form = form.upper()
                        if form not in {'N-PX', 'N-PX/A'} or not date_filed.startswith(str(year)):
                            continue
                        by_year[year].append({'year': year, 'cik': cik, 'company': company, 'form': form, 'dateFiled': date_filed, 'filename': filename})
    for year in YEARS:
        uniq = {(x['cik'], x['form'], x['dateFiled'], x['filename']): x for x in by_year[year]}
        by_year[year] = sorted(uniq.values(), key=lambda x: (x['dateFiled'], x['cik'], x['filename']))
    return by_year


def main() -> None:
    indexes = filing_indexes()
    samples = []
    for year in YEARS:
        picks = quantile_sample(indexes[year], SAMPLE_PER_YEAR)
        samples.extend(picks)
        print(f'{year} primaryNpx={sum(r["form"] == "N-PX" for r in indexes[year])} samples={len(picks)}', flush=True)

    source_results = []
    master = []
    for i, x in enumerate(samples, 1):
        try:
            text = pilot.fetch_text(pilot.sec_url(x['filename']))
            records = pilot.parse_records(text)
            paired = [r for r in records if r.get('ticker') and r.get('securityId')]
            source_results.append({**x, 'records': len(records), 'pairedRecords': len(paired)})
            for r in records:
                master.append({
                    'issuer': r['issuer'],
                    'normalizedIssuer': normalize_issuer(r['issuer']),
                    'ticker': r.get('ticker'),
                    'securityId': r.get('securityId'),
                    'sourceYear': x['year'],
                    'sourceFilingDate': x['dateFiled'],
                    'sourceCik': x['cik'],
                    'sourceCompany': x['company'],
                    'sourceFilename': x['filename'],
                })
            print(f"{i}/{len(samples)} {x['year']} {x['dateFiled']} {x['company'][:34]} records={len(records)} paired={len(paired)}", flush=True)
        except Exception as e:
            source_results.append({**x, 'error': repr(e)})
            print(f"{i}/{len(samples)} FAIL {x['year']} {x['company'][:34]} {e!r}", flush=True)
        if i < len(samples):
            time.sleep(0.6)

    unique = {}
    for r in sorted(master, key=lambda x: (x['sourceFilingDate'], x['normalizedIssuer'], x.get('ticker') or '', x.get('securityId') or '')):
        key = (r['normalizedIssuer'], r.get('ticker'), r.get('securityId'))
        unique.setdefault(key, r)
    rows = list(unique.values())
    paired = [r for r in rows if r.get('ticker') and r.get('securityId')]
    by_year = {}
    for year in YEARS:
        src = [r for r in source_results if r['year'] == year]
        ok = [r for r in src if 'error' not in r]
        by_year[str(year)] = {
            'allNpxFilings': len(indexes[year]),
            'primaryNpxFilings': sum(r['form'] == 'N-PX' for r in indexes[year]),
            'sampleCount': len(src),
            'fetchSuccess': len(ok),
            'pairedRecordsAcrossSamples': sum(r.get('pairedRecords', 0) for r in ok),
        }

    out = {
        'purpose': 'Pooled development-window N-PX issuer/ticker/security-id master for structural legacy holdings mapping. No prices or returns used.',
        'years': list(YEARS),
        'sampleRule': f'{SAMPLE_PER_YEAR} deterministic equal-quantile primary N-PX filings per sampled development year; no investment-performance selection.',
        'byYear': by_year,
        'uniqueRecords': len(rows),
        'pairedRecords': len(paired),
        'uniqueTickers': len({r['ticker'] for r in paired}),
        'uniqueSecurityIds': len({r['securityId'] for r in paired}),
        'uniqueNormalizedIssuers': len({r['normalizedIssuer'] for r in paired}),
        'records': rows,
        'sourceResults': source_results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k not in {'records', 'sourceResults'}}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
