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
OUT = ROOT / 'data' / 'research' / 'legacy-pit-holdings-development.json'
YEARS = (2006, 2008, 2010)
TARGET = re.compile(r'SELECT SECTOR SPDR|STREETTRACKS|SPDR SERIES|POWERSHARES|RYDEX ETF|PROSHARES|ISHARES', re.I)
REPORT_DATE = re.compile(r'(?im)^\s*CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$')

sspec = importlib.util.spec_from_file_location('seg', ROOT / 'scripts' / 'research-nq-series-segmentation-2006.py')
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)
pspec = importlib.util.spec_from_file_location('pit', ROOT / 'scripts' / 'research-nq-pit-holdings-2006.py')
pit = importlib.util.module_from_spec(pspec)
pspec.loader.exec_module(pit)
kspec = importlib.util.spec_from_file_location('issuer_key', ROOT / 'scripts' / 'research-legacy-issuer-key.py')
issuer_key = importlib.util.module_from_spec(kspec)
kspec.loader.exec_module(issuer_key)


def download(path: Path) -> None:
    req = urllib.request.Request(DRIVE, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
        while True:
            b = r.read(1024 * 1024)
            if not b:
                break
            f.write(b)


def iso8(raw: str | None) -> str | None:
    return f'{raw[:4]}-{raw[4:6]}-{raw[6:8]}' if raw and len(raw) == 8 else None


def load_samples() -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = defaultdict(list)
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / 'master.zip'
        download(zp)
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            for year in YEARS:
                filings = []
                qfiles = [n for n in names if any(f'master_{year}_QTR{q}.idx' in n for q in range(1, 5))]
                for name in sorted(qfiles):
                    text = z.read(name).decode('latin-1', 'replace')
                    for line in text.splitlines():
                        p = line.split('|')
                        if len(p) < 5:
                            continue
                        cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
                        if form.upper() == 'N-Q' and date_filed.startswith(str(year)) and TARGET.search(company):
                            filings.append({'cik': cik, 'company': company, 'dateFiled': date_filed, 'filename': filename})
                seen = set()
                for row in sorted(filings, key=lambda r: (r['dateFiled'], r['cik'], r['filename'])):
                    if row['cik'] in seen:
                        continue
                    seen.add(row['cik'])
                    out[year].append(row)
                    if len(out[year]) >= 8:
                        break
    return out


def issuer_holdings(holdings: list[dict]) -> list[dict]:
    out = []
    for h in holdings:
        key = issuer_key.legacy_issuer_key(str(h.get('description') or ''))
        if not key:
            continue
        out.append({
            'issuerKey': key,
            'description': h.get('description'),
            'weight': h.get('weight'),
            'marketValue': h.get('marketValue'),
            'quantityOrPrincipal': h.get('quantityOrPrincipal'),
        })
    return out


def main() -> None:
    samples = load_samples()
    records = []
    filing_results = []
    for year in YEARS:
        rows = samples[year]
        for i, x in enumerate(rows, 1):
            try:
                method, submission = seg.meta.fetch_prefix(seg.meta.sec_url(x['filename']))
                report_m = REPORT_DATE.search(submission)
                report_date = iso8(report_m.group(1) if report_m else None)
                series = [s for s in seg.meta.parse_series_contracts(submission, x['company']) if s.get('isEtf') and s.get('seriesId')]
                _, text = seg.embedded_primary_nq(submission)
                markers = list(seg.SCHEDULE.finditer(text))
                mapped = {}
                for j, marker in enumerate(markers):
                    start = marker.start()
                    end = markers[j + 1].start() if j + 1 < len(markers) else min(len(text), start + 300000)
                    parse_block = text[start:end]
                    context = text[max(0, start - 5000):min(end, start + 2500)]
                    s, score = seg.map_schedule_to_series(context, series)
                    if not s or not s.get('seriesId'):
                        continue
                    parse_method, holdings, total = pit.normalized_holdings(parse_block)
                    top10 = sum(h['weight'] for h in holdings[:10]) if holdings else 0.0
                    structurally_usable = bool(
                        seg.eligible_name(s.get('seriesName') or '')
                        and 10 <= len(holdings) <= 120
                        and total > 0
                        and top10 >= 25.0
                    )
                    candidate = {
                        'year': year,
                        'accession': pit.accession_from_filename(x['filename']),
                        'cik': x['cik'],
                        'registrant': x['company'],
                        'filingDate': x['dateFiled'],
                        'reportDate': report_date,
                        'seriesId': s['seriesId'],
                        'seriesName': s.get('seriesName'),
                        'fundTickers': s.get('etfTickers', []),
                        'mappingScore': score,
                        'parseMethod': parse_method,
                        'holdingCount': len(holdings),
                        'top10Weight': top10,
                        'parsedMarketValueTotal': total,
                        'structurallyUsable': structurally_usable,
                        'holdings': issuer_holdings(holdings) if structurally_usable else [],
                    }
                    cur = mapped.get(s['seriesId'])
                    if cur is None or (candidate['holdingCount'], score) > (cur['holdingCount'], cur['mappingScore']):
                        mapped[s['seriesId']] = candidate
                records.extend(mapped.values())
                usable = sum(r['structurallyUsable'] for r in mapped.values())
                filing_results.append({'year': year, 'company': x['company'], 'cik': x['cik'], 'transport': method, 'seriesMetadata': len(series), 'scheduleMarkers': len(markers), 'mappedSeries': len(mapped), 'usableSeries': usable})
                print(f"{year} {i}/{len(rows)} {x['company'][:40]} series={len(series)} schedules={len(markers)} mapped={len(mapped)} usable={usable}", flush=True)
            except Exception as e:
                filing_results.append({'year': year, 'company': x.get('company'), 'cik': x.get('cik'), 'error': repr(e)})
                print(f"{year} {i}/{len(rows)} FAIL {x.get('company')} {e!r}", flush=True)
            time.sleep(1.0)

    by_year = {}
    for year in YEARS:
        fr = [x for x in filing_results if x['year'] == year]
        rr = [x for x in records if x['year'] == year]
        usable_rows = [x for x in rr if x['structurallyUsable']]
        by_year[str(year)] = {
            'sampledFilings': len(fr),
            'fetchSucceeded': sum('error' not in x for x in fr),
            'mappedSeries': len(rr),
            'structurallyUsableSeries': len(usable_rows),
            'withTickerMetadata': sum(bool(x.get('fundTickers')) for x in rr),
            'issuerKeyHoldings': sum(len(x.get('holdings', [])) for x in usable_rows),
            'uniqueIssuerKeys': len({h['issuerKey'] for x in usable_rows for h in x.get('holdings', [])}),
        }

    out = {
        'purpose': 'Cross-year development-window PIT ETF-series holdings feasibility probe. Structural only; no price, return, strategy, or performance data used.',
        'years': list(YEARS),
        'sampleRule': 'Up to 8 distinct target ETF-family CIKs per sampled year; first N-Q filing in deterministic filing-date/CIK order. No parser-success or performance selection.',
        'structuralRule': 'Production-style series-name exclusion plus 10<=holdings<=120, positive parsed market value, and normalized top10 weight>=25%.',
        'identityRule': 'Retained holdings receive a conservative legacyIssuerKey derived only from contemporaneous filing description. Ticker/security-id mapping is intentionally deferred and cannot affect Universe membership.',
        'byYear': by_year,
        'filingResults': filing_results,
        'records': records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k not in {'filingResults', 'records'}}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
