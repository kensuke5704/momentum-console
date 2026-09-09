#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import socket
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/research/npx-pit-master-h2-2007-2007-12.json'
OUT_DIR = ROOT / 'data/research'
AUDIT = OUT_DIR / 'npx-pit-master-h1-2008-audit.json'
SAMPLE_COUNT = 64
SIGNALS = [
    ('2008-01', '2008-01-31'),
    ('2008-02', '2008-02-29'),
    ('2008-03', '2008-03-31'),
    ('2008-04', '2008-04-30'),
    ('2008-05', '2008-05-30'),
    ('2008-06', '2008-06-30'),
]
BROAD_CIKS = {'35348','826473','68138','745463','752737','81247','916403','814232','1039949','202385','1026708'}
INDEX_BASE = 'https://www.sec.gov/Archives/edgar/full-index/2008/QTR{q}/master.zip'
UA = {
    'User-Agent': 'Kensuke Kawamura kensuke5704@gmail.com momentum-console research',
    'Accept': 'application/zip,text/plain,text/html,*/*',
    'Accept-Encoding': 'identity',
}
MIN_INTERVAL_SECONDS = 1.15
BACKOFF_SECONDS = (3, 6, 12, 24, 36, 48)
_last_request_at = 0.0


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pilot = load_module('frozen_npx_parser', ROOT / 'scripts/research-npx-security-master-2006.py')
builder = load_module('frozen_npx_builder', ROOT / 'scripts/research-npx-security-master-build-2006.py')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def pace() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_INTERVAL_SECONDS:
        time.sleep(MIN_INTERVAL_SECONDS - elapsed)
    _last_request_at = time.monotonic()


def fetch_bytes(url: str, limit: int) -> bytes:
    last_error: Exception | None = None
    max_attempts = len(BACKOFF_SECONDS) + 1
    for attempt in range(1, max_attempts + 1):
        pace()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = response.read(limit)
            print(f'transport ok attempt={attempt} bytes={len(payload):,} url={url}', flush=True)
            return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            transient = exc.code == 429 or 500 <= exc.code <= 599
            print(f'transport HTTP attempt={attempt}/{max_attempts} code={exc.code} url={url}', flush=True)
            if not transient or attempt >= max_attempts:
                break
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
            last_error = exc
            print(f'transport transient attempt={attempt}/{max_attempts} error={exc!r} url={url}', flush=True)
            if attempt >= max_attempts:
                break
        delay = BACKOFF_SECONDS[attempt - 1]
        time.sleep(delay)
    raise RuntimeError(f'SEC transport exhausted for {url}') from last_error


def filing_index_2008() -> tuple[list[dict], list[dict]]:
    hits: list[dict] = []
    sources: list[dict] = []
    for q in (1, 2):
        url = INDEX_BASE.format(q=q)
        payload = fetch_bytes(url, 25_000_000)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            member = next((n for n in archive.namelist() if n.lower().endswith('master.idx')), None)
            if not member:
                raise RuntimeError(f'master.idx missing from {url}')
            text = archive.read(member).decode('latin-1', 'replace')
        sources.append({'quarter': q, 'transport': url})
        for line in text.splitlines():
            parts = line.split('|')
            if len(parts) < 5:
                continue
            cik, company, form, date_filed, filename = [x.strip() for x in parts[:5]]
            form = form.upper()
            if form not in {'N-PX', 'N-PX/A'} or not date_filed.startswith('2008'):
                continue
            hits.append({'cik': cik, 'company': company, 'form': form, 'dateFiled': date_filed, 'filename': filename})
    unique = {(x['cik'], x['form'], x['dateFiled'], x['filename']): x for x in hits}
    return sorted(unique.values(), key=lambda x: (x['dateFiled'], int(x['cik']), x['filename'])), sources


def representatives(public_primary: list[dict]) -> list[dict]:
    by_cik: dict[str, dict] = {}
    for row in sorted(public_primary, key=lambda x: (x['dateFiled'], int(x['cik']), x['filename'])):
        by_cik.setdefault(row['cik'], row)
    return sorted(by_cik.values(), key=lambda x: (int(x['cik']), x['dateFiled'], x['filename']))


def deterministic_quantile_sample(reps: list[dict], n: int = SAMPLE_COUNT) -> list[dict]:
    if len(reps) <= n:
        return list(reps)
    positions = [round(i * (len(reps) - 1) / (n - 1)) for i in range(n)]
    return [reps[p] for p in positions]


def source_key(row: dict) -> tuple[str, str, str, str]:
    return (row['cik'], row['form'], row['dateFiled'], row['filename'])


def record_key(row: dict) -> tuple[str, str | None, str | None]:
    return (row.get('normalizedIssuer') or '', row.get('ticker'), row.get('securityId'))


def sec_url(filename: str) -> str:
    return 'https://www.sec.gov/Archives/' + filename.lstrip('/')


def main() -> None:
    if not BASE.exists():
        raise FileNotFoundError(f'missing validated H2-2007 December N-PX base: {BASE}')
    base = json.loads(BASE.read_text())
    if base.get('signalMonth') != '2007-12' or base.get('asOf') != '2007-12-31':
        raise RuntimeError('unexpected H2-2007 base boundary')
    base_records = list(base.get('records', []))
    base_keys = [record_key(r) for r in base_records]
    if len(base_keys) != len(set(base_keys)):
        raise RuntimeError('validated base contains duplicate identity keys')

    filings, index_sources = filing_index_2008()
    primary = [x for x in filings if x['form'] == 'N-PX']
    amendments = [x for x in filings if x['form'] == 'N-PX/A']
    print('INDEX', json.dumps({'total': len(filings), 'primary': len(primary), 'amendments': len(amendments), 'months': dict(Counter(x['dateFiled'][:7] for x in filings))}), flush=True)

    admitted: dict[tuple[str, str, str, str], dict] = {}
    month_selection: dict[str, dict] = {}
    for signal_month, as_of in SIGNALS:
        public_primary = [x for x in primary if x['dateFiled'] <= as_of]
        reps = representatives(public_primary)
        sampled = deterministic_quantile_sample(reps)
        broad = [x for x in reps if x['cik'] in BROAD_CIKS]
        selected = {source_key(x): x for x in sampled + broad}
        new_keys = []
        for key, row in sorted(selected.items(), key=lambda kv: (kv[1]['dateFiled'], int(kv[1]['cik']), kv[1]['filename'])):
            if key not in admitted:
                admitted[key] = {**row, 'admittedAtSignal': as_of}
                new_keys.append(key)
        month_selection[signal_month] = {
            'signalMonth': signal_month, 'asOf': as_of,
            'publicPrimaryFilings': len(public_primary), 'publicRepresentativeCiks': len(reps),
            'quantileSelectedSources': len(sampled), 'broadSelectedSources': len(broad),
            'selectedUniqueSources': len(selected), 'newAdmissions': len(new_keys),
            'cumulativeAdmissions': len(admitted),
        }
        print('SELECTION', json.dumps(month_selection[signal_month]), flush=True)

    parsed_by_source: dict[tuple[str, str, str, str], list[dict]] = {}
    source_results = []
    fetch_errors = []
    admitted_rows = sorted(admitted.values(), key=lambda x: (x['dateFiled'], int(x['cik']), x['filename']))
    for i, source in enumerate(admitted_rows, 1):
        key = source_key(source)
        try:
            payload = fetch_bytes(sec_url(source['filename']), 20_000_000)
            text = payload.decode('latin-1', 'replace')
            parsed = pilot.parse_records(text)
            rows = []
            for rec in parsed:
                rows.append({
                    'issuer': rec['issuer'], 'normalizedIssuer': builder.normalize_issuer(rec['issuer']),
                    'ticker': rec.get('ticker'), 'securityId': rec.get('securityId'),
                    'meetingDateRaw': rec.get('meetingDateRaw'), 'sourceFilingDate': source['dateFiled'],
                    'sourceCik': source['cik'], 'sourceCompany': source['company'], 'sourceFilename': source['filename'],
                    'admittedAtSignal': source['admittedAtSignal'], 'sourceForm': source['form'],
                })
            parsed_by_source[key] = rows
            source_results.append({**source, 'fetchOk': True, 'records': len(rows), 'pairedRecords': sum(bool(r.get('ticker') and r.get('securityId')) for r in rows)})
        except Exception as exc:
            fetch_errors.append({**source, 'error': repr(exc)})
            source_results.append({**source, 'fetchOk': False, 'error': repr(exc)})
        print(f'SOURCE {i}/{len(admitted_rows)} CIK={source["cik"]} ok={key in parsed_by_source}', flush=True)

    violations = []
    if fetch_errors:
        violations.append({'type': 'FETCH_ERRORS', 'count': len(fetch_errors)})
    monthly = []
    previous_active: set[tuple[str, str, str, str]] = set()
    for signal_month, as_of in SIGNALS:
        active_sources = {k: r for k, r in admitted.items() if r['admittedAtSignal'] <= as_of and r['dateFiled'] <= as_of}
        active_keys = set(active_sources)
        if not previous_active.issubset(active_keys):
            violations.append({'signalMonth': signal_month, 'type': 'NON_MONOTONE_SOURCE_SET'})
        previous_active = active_keys
        records = list(base_records)
        seen = set(base_keys)
        incremental_candidates = incremental_added = 0
        incremental_source_dates: list[str] = []
        for key, source in sorted(active_sources.items(), key=lambda kv: (kv[1]['dateFiled'], int(kv[1]['cik']), kv[1]['filename'])):
            if source['form'] != 'N-PX':
                violations.append({'signalMonth': signal_month, 'type': 'NON_PRIMARY_ADMISSION', 'source': source})
            if source['dateFiled'] > as_of or source['admittedAtSignal'] > as_of:
                violations.append({'signalMonth': signal_month, 'type': 'LOOKAHEAD_SOURCE', 'source': source})
                continue
            for row in parsed_by_source.get(key, []):
                incremental_candidates += 1
                if row['sourceFilingDate'] > as_of or row['admittedAtSignal'] > as_of:
                    violations.append({'signalMonth': signal_month, 'type': 'LOOKAHEAD_RECORD', 'record': row})
                    continue
                incremental_source_dates.append(row['sourceFilingDate'])
                rkey = record_key(row)
                if rkey in seen:
                    continue
                seen.add(rkey)
                records.append(row)
                incremental_added += 1
        if records[:len(base_records)] != base_records:
            violations.append({'signalMonth': signal_month, 'type': 'BASE_MUTATED'})
        out = {
            'year': 2008, 'signalMonth': signal_month, 'asOf': as_of,
            'purpose': 'H1 2008 PIT N-PX identity master: immutable validated 2007-12 master plus only 2008 evidence public/admitted by signal date.',
            'baseRunId': 34190105652, 'baseArtifactId': 10041975282, 'baseSha256': sha256_file(BASE),
            'baseRecordCount': len(base_records), 'activeIncrementalSourceCount': len(active_sources),
            'incrementalParsedRecordCandidates': incremental_candidates, 'incrementalUniqueRecordsAdded': incremental_added,
            'pairedRecords': sum(bool(r.get('ticker') and r.get('securityId')) for r in records), 'uniqueRecords': len(records),
            'records': records, 'incrementalSources': [active_sources[k] for k in sorted(active_sources)],
        }
        out_path = OUT_DIR / f'npx-pit-master-h1-2008-{signal_month}.json'
        out_path.write_text(json.dumps(out, indent=2) + '\n')
        monthly.append({
            **month_selection[signal_month], 'activeIncrementalSources': len(active_sources),
            'incrementalParsedRecordCandidates': incremental_candidates, 'incrementalUniqueRecordsAdded': incremental_added,
            'totalMasterRecords': len(records), 'pairedRecords': out['pairedRecords'],
            'maxIncrementalSourceFilingDate': max(incremental_source_dates) if incremental_source_dates else None,
            'output': str(out_path.relative_to(ROOT)),
        })
        print('MONTH', json.dumps(monthly[-1]), flush=True)

    audit = {
        'status': 'PASS' if not violations else 'FAIL',
        'purpose': 'Pre-mapping PIT validation for H1 2008 N-PX identity masters; no N-Q mapping coverage, country, Universe, return, or strategy outcome used.',
        'definition': 'docs/research/h1-2008-npx-pit-master-validation-definition.md',
        'baseRunId': 34190105652, 'baseArtifactId': 10041975282, 'baseSha256': sha256_file(BASE),
        'baseRecordCount': len(base_records), 'indexSources': index_sources,
        'inventory': {'allNpxAndAmendments': len(filings), 'primaryNpx': len(primary), 'npxAmendments': len(amendments), 'uniquePrimaryCiks': len({x['cik'] for x in primary}), 'filingMonthCounts': dict(sorted(Counter(x['dateFiled'][:7] for x in filings).items()))},
        'broadCiks': sorted(BROAD_CIKS, key=int), 'sampleCount': SAMPLE_COUNT,
        'admittedSourceCount': len(admitted), 'fetchErrorCount': len(fetch_errors), 'fetchErrors': fetch_errors,
        'sourceResults': source_results, 'monthly': monthly, 'violations': violations,
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + '\n')
    print('H1_2008_NPX_PIT_SUMMARY', json.dumps({'status': audit['status'], 'inventory': audit['inventory'], 'admittedSourceCount': len(admitted), 'fetchErrorCount': len(fetch_errors), 'monthly': monthly}), flush=True)
    if violations:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
