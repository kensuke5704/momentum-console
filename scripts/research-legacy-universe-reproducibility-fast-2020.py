#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

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


def _block_fingerprint(holdings: list[dict], total: float) -> tuple:
    names = tuple(sorted(str(h.get('description') or '').strip().upper() for h in holdings))
    return names, round(float(total or 0), 6)


def structural_mapped_modern_series(text: str, series: list[dict]):
    """Exact-heading mapping plus raw-value merge of all valid blocks per series.

    Shareholder reports can split one ETF across repeated Portfolio/Schedule headings.
    Every source block must pass structural sanity independently. Valid blocks are
    converted from normalized weights back to raw market value, deduplicated, merged,
    then normalized once at series level. No prices, returns, concentration targets,
    strategy ranks, or backtest output are used.
    """
    blocks = repro.ov.schedule_blocks(text)
    unique_name_matches = parsed_nonempty = structural_block_pass = 0
    examples = []
    grouped: dict[str, dict] = {}

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
        if count:
            parsed_nonempty += 1
        sane = bool(holdings and repro.ov.pit.legacy_holdings.structural_sanity(holdings))
        block_gate = bool(repro.ov.seg.eligible_name(s.get('seriesName') or '') and count >= 2 and total > 0 and sane)
        if block_gate:
            structural_block_pass += 1
            g = grouped.setdefault(s['seriesId'], {'series': s, 'blocks': [], 'fingerprints': set()})
            fp = _block_fingerprint(holdings, total)
            if fp not in g['fingerprints']:
                g['fingerprints'].add(fp)
                g['blocks'].append({'method': method, 'holdings': holdings, 'total': float(total)})
        if len(examples) < 30:
            examples.append({
                'seriesId': s.get('seriesId'), 'seriesName': s.get('seriesName'),
                'method': method, 'holdingCount': count, 'total': total,
                'structuralSanity': sane, 'structuralBlockGate': block_gate,
            })

    mapped = {}
    merge_diag = []
    for sid, g in grouped.items():
        raw_by_desc = defaultdict(float)
        methods = []
        for b in g['blocks']:
            methods.append(b['method'])
            total = b['total']
            for h in b['holdings']:
                desc = str(h.get('description') or '').strip()
                weight = float(h.get('weight') or 0)
                if desc and weight > 0:
                    raw_by_desc[desc] += total * weight / 100.0
        merged_total = sum(raw_by_desc.values())
        holdings = [
            {
                'description': desc,
                'marketValue': value,
                'weight': 100.0 * value / merged_total,
            }
            for desc, value in raw_by_desc.items()
            if value > 0 and merged_total > 0
        ]
        holdings.sort(key=lambda h: -h['weight'])
        final_sane = bool(holdings and repro.ov.pit.legacy_holdings.structural_sanity(holdings))
        final_gate = bool(10 <= len(holdings) <= 3000 and merged_total > 0 and final_sane)
        merge_diag.append({
            'seriesId': sid, 'seriesName': g['series'].get('seriesName'),
            'mergedBlockCount': len(g['blocks']), 'mergedHoldingCount': len(holdings),
            'mergedTotal': merged_total, 'structuralSanity': final_sane, 'finalGate': final_gate,
        })
        if final_gate:
            mapped[sid] = {
                'seriesId': sid,
                'seriesName': g['series'].get('seriesName'),
                'fundTickers': g['series'].get('etfTickers', []),
                'holdings': holdings,
                'method': f"merged-{len(g['blocks'])}-blocks:" + ','.join(sorted(set(methods))),
                'total': merged_total,
                'top10': sum(h['weight'] for h in holdings[:10]),
            }

    print('LEGACY_INVESTMENT_HEADING_BLOCKS', len(blocks), flush=True)
    print('LEGACY_UNIQUE_SERIES_NAME_MATCHES', unique_name_matches, flush=True)
    print('LEGACY_PARSED_NONEMPTY_BLOCKS', parsed_nonempty, flush=True)
    print('LEGACY_STRUCTURAL_BLOCKS', structural_block_pass, flush=True)
    print('LEGACY_MAPPED_SERIES', len(mapped), sorted(mapped), flush=True)
    print('LEGACY_BLOCK_DIAGNOSTIC_EXAMPLES', json.dumps(examples, sort_keys=True), flush=True)
    print('LEGACY_MERGE_DIAGNOSTICS', json.dumps(merge_diag, sort_keys=True), flush=True)
    return mapped


repro.ov.master_2020 = fixed_fixture_sample
repro.ov.seg.meta.parse_series_contracts = shared_nport_series_contracts
repro.ov.mapped_modern_series = structural_mapped_modern_series
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'


if __name__ == '__main__':
    repro.main()
