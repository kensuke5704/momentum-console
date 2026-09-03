#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import io
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'sec-series-class-reference-2020.json'
URL = 'https://www.sec.gov/files/investment/data/other/investment-company-series-and-class-information/investment_company_series_class_2020.csv'
FETCH_URLS = (
    URL,
    'https://r.jina.ai/https://www.sec.gov/files/investment/data/other/investment-company-series-and-class-information/investment_company_series_class_2020.csv',
    'https://r.jina.ai/http://www.sec.gov/files/investment/data/other/investment-company-series-and-class-information/investment_company_series_class_2020.csv',
)
UA = {
    'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com',
    'Accept': 'text/csv,text/plain,*/*',
}


def decode(raw: bytes) -> str:
    for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode('latin-1', 'replace')


def trim_proxy_preamble(text: str) -> str:
    # Jina can prepend a short metadata block before raw text. Start at the first
    # line that looks like the SEC CSV header instead of assuming byte zero.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        u = line.upper()
        if 'SERIES' in u and 'CIK' in u and ',' in line:
            return '\n'.join(lines[i:]) + '\n'
    return text


def fetch_csv() -> tuple[str, str]:
    errors = []
    for url in FETCH_URLS:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            text = trim_proxy_preamble(decode(raw))
            if 'SERIES' not in text.upper() or 'CIK' not in text.upper():
                raise RuntimeError(f'payload does not look like series/class CSV; bytes={len(raw)}')
            return url, text
        except Exception as e:
            errors.append(f'{url}: {e!r}')
    raise RuntimeError('All series/class fetch routes failed: ' + ' | '.join(errors))


def norm_header(x: str) -> str:
    return ''.join(ch.lower() for ch in str(x or '') if ch.isalnum())


def find_field(fields: list[str], needles: tuple[str, ...]) -> str | None:
    keyed = {norm_header(f): f for f in fields}
    for needle in needles:
        n = norm_header(needle)
        if n in keyed:
            return keyed[n]
    for k, original in keyed.items():
        if any(norm_header(n) in k for n in needles):
            return original
    return None


def main() -> None:
    fetch_url, text = fetch_csv()
    reader = csv.DictReader(io.StringIO(text))
    fields = list(reader.fieldnames or [])
    rows = list(reader)

    series_field = find_field(fields, ('Series ID', 'SeriesId'))
    cik_field = find_field(fields, ('CIK Number', 'CIK'))
    registrant_field = find_field(fields, ('Name of Registrant', 'Registrant Name', 'Registrant'))
    series_name_field = find_field(fields, ('Series Name',))
    class_field = find_field(fields, ('Class Contract ID', 'Class ID', 'Class Contract'))
    ticker_field = find_field(fields, ('Ticker Symbol', 'Ticker'))
    if not series_field or not cik_field:
        raise RuntimeError(f'Unable to resolve required fields. headers={fields!r}')

    ref: dict[str, dict] = {}
    for r in rows:
        sid = str(r.get(series_field) or '').strip()
        cik = str(r.get(cik_field) or '').strip().lstrip('0') or '0'
        if not sid.startswith('S'):
            continue
        entry = ref.setdefault(sid, {
            'seriesId': sid,
            'cik': cik,
            'registrantName': str(r.get(registrant_field) or '').strip() if registrant_field else None,
            'seriesName': str(r.get(series_name_field) or '').strip() if series_name_field else None,
            'classes': [],
        })
        cls = str(r.get(class_field) or '').strip() if class_field else ''
        ticker = str(r.get(ticker_field) or '').strip() if ticker_field else ''
        if cls or ticker:
            entry['classes'].append({'classId': cls or None, 'ticker': ticker or None})

    with gzip.open(BOOT, 'rt', encoding='utf-8') as f:
        bp = json.load(f)
    snapshots = bp.get('snapshots') or bp.get('filings') or []
    prod_ids = sorted({str(x.get('seriesId') or '') for x in snapshots if str(x.get('reportDate') or '').startswith('2020') and x.get('seriesId')})
    matched = [sid for sid in prod_ids if sid in ref]
    missing = [sid for sid in prod_ids if sid not in ref]

    by_cik: dict[str, set[str]] = defaultdict(set)
    for sid in matched:
        by_cik[ref[sid]['cik']].add(sid)
    groups = []
    for cik, sids in by_cik.items():
        first = ref[sorted(sids)[0]]
        groups.append({
            'cik': cik,
            'registrantName': first.get('registrantName'),
            'seriesCount': len(sids),
            'seriesIds': sorted(sids),
            'seriesNames': sorted({str(ref[s].get('seriesName') or '') for s in sids}),
        })
    groups.sort(key=lambda g: (-g['seriesCount'], int(g['cik']) if g['cik'].isdigit() else 10**20, str(g.get('registrantName') or '')))

    out = {
        'purpose': 'Map the frozen Production 2020 N-PORT series IDs to true SEC registrant identities using the official Investment Company Series/Class reference. No accession-prefix CIK inference, prices, returns, or strategy outputs are used.',
        'sourceUrl': URL,
        'fetchUrl': fetch_url,
        'sourceHeaders': fields,
        'resolvedFields': {
            'seriesId': series_field,
            'cik': cik_field,
            'registrantName': registrant_field,
            'seriesName': series_name_field,
            'classId': class_field,
            'ticker': ticker_field,
        },
        'referenceSeriesCount': len(ref),
        'production2020SeriesCount': len(prod_ids),
        'matchedProductionSeriesCount': len(matched),
        'matchedProductionSeriesRate': len(matched) / len(prod_ids) if prod_ids else None,
        'trueRegistrantCount': len(groups),
        'registrants': groups,
        'missingProductionSeriesIds': missing,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k not in {'registrants', 'missingProductionSeriesIds', 'sourceHeaders'}}, sort_keys=True), flush=True)
    for g in groups[:30]:
        print('REGISTRANT', g['cik'], g.get('registrantName'), 'series', g['seriesCount'], 'examples', g['seriesNames'][:5], flush=True)
    if missing:
        print('MISSING_SERIES', len(missing), missing[:30], flush=True)


if __name__ == '__main__':
    main()
