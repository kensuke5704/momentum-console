#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

# Frozen structural fixture. This accession was selected because the registrant is a
# multi-series ETF trust with a June 30, 2020 shareholder report and therefore gives
# the legacy parser enough same-date series to exercise the reproducibility gates.
# Selection uses no prices, returns, ranks, parser-success feedback, or strategy output.
FIXTURE_FILINGS = (
    {
        'cik': '1510337',
        'company': 'First Trust Exchange-Traded AlphaDEX Fund II',
        'form': 'N-CSRS',
        'dateFiled': '2020-08-31',
        'filename': 'edgar/data/1510337/0001445546-20-004251.txt',
        'accession': '0001445546-20-004251',
        'fixtureBasis': 'SEC accession with report period 2020-06-30; multi-series ETF registrant',
    },
)


def fixed_fixture_sample():
    rows = [dict(x) for x in FIXTURE_FILINGS]
    print('FIXED_STRUCTURAL_FILINGS', len(rows), [x['accession'] for x in rows], flush=True)
    return rows


def shared_nport_series_contracts(_submission: str, _company: str):
    """Supply only series identity metadata from the frozen N-PORT side."""
    with gzip.open(repro.BOOTSTRAP, 'rt', encoding='utf-8') as f:
        bp = json.load(f)
    rows = bp.get('snapshots') or bp.get('filings') or []
    by_id = {}
    for row in rows:
        sid = str(row.get('seriesId') or '').strip()
        name = str(row.get('seriesName') or '').strip()
        if not sid or not name:
            continue
        by_id.setdefault(sid, {'seriesId': sid, 'seriesName': name, 'isEtf': True, 'etfTickers': []})
    out = list(by_id.values())
    print('FROZEN_SHARED_SERIES_IDENTITIES', len(out), flush=True)
    return out


_original_normalized_holdings = repro.ov.pit.normalized_holdings


def normalized_holdings_with_empty_fallback(block: str):
    """Preserve valid primary parses; fallback only for empty/year-artifact parses."""
    method, holdings, total = _original_normalized_holdings(block)
    needs_fallback = not holdings or repro.ov.pit._year_header_artifact(holdings, total)
    if not needs_fallback:
        return method, holdings, total

    fallback_raw = repro.ov.pit.legacy_holdings.parse_html_table(block)
    fallback, fallback_total = repro.ov.pit._normalize(fallback_raw)
    if len(fallback) >= 2 and fallback_total > 0 and repro.ov.pit.legacy_holdings.structural_sanity(fallback):
        reason = 'empty-primary' if not holdings else 'year-artifact'
        return f'html-{reason}-fallback', fallback, fallback_total
    return method, holdings, total


repro.ov.pit.normalized_holdings = normalized_holdings_with_empty_fallback
_original_mapped_modern_series = repro.ov.mapped_modern_series


def diagnostic_mapped_modern_series(text: str, series: list[dict]):
    blocks = repro.ov.schedule_blocks(text)
    print('LEGACY_INVESTMENT_HEADING_BLOCKS', len(blocks), flush=True)
    unique_name_matches = 0
    parsed_nonempty = 0
    structural_gate_pass = 0
    examples = []
    for start, end in blocks:
        block = text[start:end]
        context = text[max(0, start - 10000):min(end, start + 3000)]
        v = repro.ov.norm_series_text(repro.ov.visible(context))
        exact = []
        for s in series:
            name = repro.ov.norm_series_text(s.get('seriesName') or '')
            if name and name in v:
                exact.append(s)
        if len(exact) != 1:
            continue
        unique_name_matches += 1
        s = exact[0]
        method, holdings, total = repro.ov.pit.normalized_holdings(block)
        count = len(holdings)
        top10 = sum(h['weight'] for h in holdings[:10]) if holdings else 0
        if count:
            parsed_nonempty += 1
        gate = bool(
            repro.ov.seg.eligible_name(s.get('seriesName') or '')
            and 10 <= count <= 120
            and total > 0
            and top10 >= 25
        )
        if gate:
            structural_gate_pass += 1
        if len(examples) < 20:
            examples.append({
                'seriesId': s.get('seriesId'),
                'seriesName': s.get('seriesName'),
                'method': method,
                'holdingCount': count,
                'total': total,
                'top10': top10,
                'structuralGate': gate,
            })
    print('LEGACY_UNIQUE_SERIES_NAME_MATCHES', unique_name_matches, flush=True)
    print('LEGACY_PARSED_NONEMPTY_BLOCKS', parsed_nonempty, flush=True)
    print('LEGACY_STRUCTURAL_GATE_BLOCKS', structural_gate_pass, flush=True)
    print('LEGACY_BLOCK_DIAGNOSTIC_EXAMPLES', json.dumps(examples, sort_keys=True), flush=True)
    return _original_mapped_modern_series(text, series)


repro.ov.master_2020 = fixed_fixture_sample
repro.ov.seg.meta.parse_series_contracts = shared_nport_series_contracts
repro.ov.mapped_modern_series = diagnostic_mapped_modern_series
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'
repro.main()
