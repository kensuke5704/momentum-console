#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / 'pacer-parity-diagnostic-2020.json'
BOOT = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'

fspec = importlib.util.spec_from_file_location('fast', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-fast-2020.py')
fast = importlib.util.module_from_spec(fspec); fspec.loader.exec_module(fast)
mspec = importlib.util.spec_from_file_location('meta', ROOT / 'scripts' / 'research-nq-series-metadata-2006.py')
meta = importlib.util.module_from_spec(mspec); mspec.loader.exec_module(meta)
ispec = importlib.util.spec_from_file_location('aliases', ROOT / 'scripts' / 'research-legacy-issuer-aliases.py')
aliases = importlib.util.module_from_spec(ispec); ispec.loader.exec_module(aliases)

FILING = {
    'cik': '1616668',
    'company': 'Pacer Funds Trust',
    'dateFiled': '2020-07-08',
    'filename': 'edgar/data/1616668/0001398344-20-013455.txt',
    'accession': '0001398344-20-013455',
}
TARGET_SIDS = {'S000048688', 'S000062278', 'S000052000', 'S000055466', 'S000055468', 'S000048686'}


def issuer_aliases(raw: str) -> list[str]:
    return aliases.issuer_aliases(raw, fast.repro.ov.norm_issuer)


def unique_map(holdings: list[dict]) -> dict[str, str]:
    m = defaultdict(set)
    for h in holdings:
        sym = str(h.get('symbol') or '').strip().upper()
        if not sym:
            continue
        for a in issuer_aliases(str(h.get('issuerName') or '')):
            m[a].add(sym)
    return {a: next(iter(ss)) for a, ss in m.items() if len(ss) == 1}


def main() -> None:
    transport, submission = fast.repro.ov.fetch_full_filing(fast.repro.ov.seg.meta.sec_url(FILING['filename']))
    report_match = fast.repro.ov.REPORT_DATE.search(submission)
    report = fast.repro.ov.iso8(report_match.group(1) if report_match else None)
    series = [
        s for s in meta.parse_series_contracts(submission, FILING['company'])
        if s.get('seriesId') and s.get('seriesName') and s.get('productionSeriesNameEligible')
    ]
    mapped = fast.structural_mapped_modern_series(fast.repro.ov.embedded_csr(submission), series)

    with gzip.open(BOOT, 'rt', encoding='utf-8') as f:
        bp = json.load(f)
    nport = bp.get('snapshots') or bp.get('filings') or []
    by_sid = defaultdict(list)
    for r in nport:
        if r.get('seriesId') and r.get('reportDate'):
            by_sid[str(r['seriesId'])].append(r)

    diagnostics = []
    for sid in sorted(TARGET_SIDS):
        row = mapped.get(sid)
        candidates = by_sid.get(sid, [])
        if not row or not candidates or not report:
            diagnostics.append({'seriesId': sid, 'status': 'missing-side', 'legacyMapped': bool(row), 'nportSnapshots': len(candidates)})
            continue
        nearest = min(candidates, key=lambda r: fast.repro.days_between(report, str(r['reportDate'])))
        umap = unique_map(nearest.get('holdings', []))
        legacy_rows = []
        for h in row.get('holdings', []):
            desc = str(h.get('description') or '').strip()
            matched = None
            matched_alias = None
            for a in issuer_aliases(desc):
                if a in umap:
                    matched = umap[a]; matched_alias = a; break
            legacy_rows.append({'description': desc, 'weight': h.get('weight'), 'matchedSymbol': matched, 'matchedAlias': matched_alias})
        nport_rows = [
            {'issuerName': h.get('issuerName'), 'symbol': h.get('symbol'), 'weight': h.get('weight')}
            for h in nearest.get('holdings', [])
            if h.get('symbol') and float(h.get('weight') or 0) > 0
        ]
        matched_syms = {r['matchedSymbol'] for r in legacy_rows if r['matchedSymbol']}
        diagnostics.append({
            'seriesId': sid,
            'seriesName': row.get('seriesName'),
            'legacyReportDate': report,
            'nportReportDate': nearest.get('reportDate'),
            'nportFilingDate': nearest.get('filingDate'),
            'legacyHoldingCount': len(legacy_rows),
            'legacyMatchedCount': sum(1 for r in legacy_rows if r['matchedSymbol']),
            'nportHoldingCount': len(nport_rows),
            'nportSymbolsMissingFromLegacyMatchCount': sum(1 for r in nport_rows if str(r.get('symbol') or '').upper() not in matched_syms),
            'legacyTop20': sorted(legacy_rows, key=lambda r: -(float(r.get('weight') or 0)))[:20],
            'legacyUnmatchedTop30': sorted([r for r in legacy_rows if not r['matchedSymbol']], key=lambda r: -(float(r.get('weight') or 0)))[:30],
            'nportMissingFromLegacyTop30': sorted([r for r in nport_rows if str(r.get('symbol') or '').upper() not in matched_syms], key=lambda r: -(float(r.get('weight') or 0)))[:30],
        })

    out = {
        'purpose': 'Structural same-report diagnostic for Pacer legacy shareholder-report parsing versus frozen Production N-PORT. No prices, returns, ranks, trades or strategy outputs are used.',
        'filing': FILING,
        'transport': transport,
        'reportDate': report,
        'productionEligibleSeriesInFiling': len(series),
        'mappedSeries': len(mapped),
        'diagnostics': diagnostics,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print('SUMMARY', json.dumps({k:v for k,v in out.items() if k != 'diagnostics'}, sort_keys=True), flush=True)
    for x in diagnostics:
        print('SERIES_DIAG', json.dumps({k:v for k,v in x.items() if k not in {'legacyTop20','legacyUnmatchedTop30','nportMissingFromLegacyTop30'}}, sort_keys=True), flush=True)

if __name__ == '__main__':
    main()
