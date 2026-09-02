#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-2020.json'

spec = importlib.util.spec_from_file_location('ov', ROOT / 'scripts' / 'research-ncsr-nport-overlap-2020.py')
ov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ov)

DAY_DECAY = 120.0
TOP_N = 80


def days_between(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def score_universe(filings: list[dict], as_of: str) -> list[dict]:
    rows: dict[str, dict] = {}
    for f in filings:
        filed = f.get('filingDate') or as_of
        age = max(0, (date.fromisoformat(as_of) - date.fromisoformat(filed)).days)
        recency = math.exp(-age / DAY_DECAY)
        sid = f['seriesId']
        for h in f.get('holdings', []):
            symbol = str(h.get('symbol') or '').strip().upper()
            weight = float(h.get('weight') or 0)
            if not symbol or weight <= 0:
                continue
            row = rows.setdefault(symbol, {'seriesIds': set(), 'aggregateWeight': 0.0, 'maxWeight': 0.0, 'recencyWeight': 0.0})
            row['seriesIds'].add(sid)
            row['aggregateWeight'] += weight
            row['maxWeight'] = max(row['maxWeight'], weight)
            row['recencyWeight'] += weight * recency

    out = []
    for symbol, row in rows.items():
        etf_count = len(row['seriesIds'])
        if not (etf_count >= 2 or row['maxWeight'] >= 4):
            continue
        score = 3 * math.log1p(etf_count) + 0.5 * math.log1p(row['aggregateWeight']) + 0.5 * math.log1p(row['recencyWeight'])
        out.append({
            'symbol': symbol,
            'etfCount': etf_count,
            'aggregateWeight': row['aggregateWeight'],
            'maxWeight': row['maxWeight'],
            'recencyWeight': row['recencyWeight'],
            'universeScore': score,
        })
    out.sort(key=lambda r: (-r['universeScore'], -r['etfCount'], -r['aggregateWeight'], r['symbol']))
    for i, row in enumerate(out, 1):
        row['rank'] = i
    return out


def rank_corr(a: dict[str, int], b: dict[str, int], symbols: set[str]) -> float | None:
    if len(symbols) < 3:
        return None
    xs = [float(a[s]) for s in sorted(symbols)]
    ys = [float(b[s]) for s in sorted(symbols)]
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    denx = sum((x-mx)**2 for x in xs); deny = sum((y-my)**2 for y in ys)
    den = math.sqrt(denx*deny)
    return num/den if den else None


def main() -> None:
    filings = ov.master_2020()
    latest_by_cik = {}
    for x in sorted(filings, key=lambda r: (r['dateFiled'], r['filename'])):
        latest_by_cik[x['cik']] = x
    chosen = [latest_by_cik[cik] for cik in sorted(latest_by_cik)]

    with gzip.open(BOOTSTRAP, 'rt', encoding='utf-8') as f:
        bp = json.load(f)
    nport = bp.get('snapshots') or bp.get('filings') or []
    by_series = defaultdict(list)
    for f in nport:
        if f.get('seriesId') and f.get('reportDate'):
            by_series[f['seriesId']].append(f)
    for rows in by_series.values():
        rows.sort(key=lambda r: (r.get('reportDate',''), r.get('filingDate','')))

    legacy_filings = []
    nport_filings = []
    series_diag = []
    filing_diag = []

    for i, x in enumerate(chosen, 1):
        try:
            transport, submission = ov.fetch_full_filing(ov.seg.meta.sec_url(x['filename']))
            rm = ov.REPORT_DATE.search(submission)
            report = ov.iso8(rm.group(1) if rm else None)
            series = [s for s in ov.seg.meta.parse_series_contracts(submission, x['company']) if s.get('isEtf') and s.get('seriesId')]
            mapped = ov.mapped_modern_series(ov.embedded_csr(submission), series)
            matched = 0
            for sid, row in mapped.items():
                candidates = by_series.get(sid, [])
                if not report or not candidates:
                    continue
                nearest = min(candidates, key=lambda f: days_between(report, f['reportDate']))
                gap = days_between(report, nearest['reportDate'])
                if gap > 45:
                    continue

                issuer_to_symbols = defaultdict(set)
                for h in nearest.get('holdings', []):
                    issuer = ov.norm_issuer(str(h.get('issuerName') or ''))
                    symbol = str(h.get('symbol') or '').strip().upper()
                    if issuer and symbol:
                        issuer_to_symbols[issuer].add(symbol)
                unique_map = {k: next(iter(v)) for k,v in issuer_to_symbols.items() if len(v) == 1}

                legacy_symbol_weights = defaultdict(float)
                legacy_total = 0.0
                legacy_mapped = 0.0
                for h in row.get('holdings', []):
                    w = float(h.get('weight') or 0)
                    if w <= 0:
                        continue
                    legacy_total += w
                    issuer = ov.norm_issuer(str(h.get('description') or ''))
                    symbol = unique_map.get(issuer)
                    if symbol:
                        legacy_symbol_weights[symbol] += w
                        legacy_mapped += w

                nport_symbol_weights = defaultdict(float)
                for h in nearest.get('holdings', []):
                    symbol = str(h.get('symbol') or '').strip().upper()
                    w = float(h.get('weight') or 0)
                    if symbol and w > 0:
                        nport_symbol_weights[symbol] += w

                if not legacy_symbol_weights or not nport_symbol_weights:
                    series_diag.append({'seriesId':sid,'seriesName':row.get('seriesName'),'status':'no-symbol-holdings','reportGapDays':gap})
                    continue

                legacy_filings.append({
                    'seriesId': sid,
                    'filingDate': x['dateFiled'],
                    'holdings': [{'symbol':s,'weight':w} for s,w in sorted(legacy_symbol_weights.items())],
                })
                nport_filings.append({
                    'seriesId': sid,
                    'filingDate': str(nearest.get('filingDate') or x['dateFiled']),
                    'holdings': [{'symbol':s,'weight':w} for s,w in sorted(nport_symbol_weights.items())],
                })
                matched += 1
                series_diag.append({
                    'seriesId': sid,
                    'seriesName': row.get('seriesName'),
                    'legacyReportDate': report,
                    'nportReportDate': nearest.get('reportDate'),
                    'reportGapDays': gap,
                    'legacyHoldingCount': len(row.get('holdings', [])),
                    'legacyMappedSymbolCount': len(legacy_symbol_weights),
                    'nportSymbolCount': len(nport_symbol_weights),
                    'legacySymbolWeightCoverage': legacy_mapped / legacy_total if legacy_total else None,
                    'parseMethod': row.get('method'),
                    'status': 'paired',
                })
            filing_diag.append({'company':x['company'],'cik':x['cik'],'transport':transport,'registeredEtfSeries':len(series),'usableMappedSeries':len(mapped),'pairedSeries':matched})
            print(f"{i}/{len(chosen)} {x['company'][:42]} mapped={len(mapped)} paired={matched}", flush=True)
        except Exception as e:
            filing_diag.append({'company':x.get('company'),'cik':x.get('cik'),'error':repr(e)})
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}", flush=True)

    paired = [x for x in series_diag if x.get('status') == 'paired']
    all_dates = [f['filingDate'] for f in legacy_filings+nport_filings if f.get('filingDate')]
    as_of = max(all_dates) if all_dates else '2020-12-31'
    legacy_ranked = score_universe(legacy_filings, as_of)
    nport_ranked = score_universe(nport_filings, as_of)
    legacy_top = legacy_ranked[:TOP_N]
    nport_top = nport_ranked[:TOP_N]
    ls = {x['symbol'] for x in legacy_top}; ns = {x['symbol'] for x in nport_top}; common = ls & ns
    lr = {x['symbol']:x['rank'] for x in legacy_top}; nr = {x['symbol']:x['rank'] for x in nport_top}
    denom = min(TOP_N, len(legacy_top), len(nport_top))
    overlap_rate = len(common)/denom if denom else None
    jaccard = len(common)/len(ls|ns) if (ls|ns) else None
    spearman = rank_corr(lr,nr,common)
    coverages = sorted(x['legacySymbolWeightCoverage'] for x in paired if x.get('legacySymbolWeightCoverage') is not None)
    median_cov = statistics.median(coverages) if coverages else None

    # Predeclared structural gate. This is a paired-series test, not yet the final
    # full-production-universe gate because only series observable in both legacy
    # shareholder reports and N-PORT are included.
    gate = bool(
        len(paired) >= 10
        and median_cov is not None and median_cov >= 0.80
        and overlap_rate is not None and overlap_rate >= 0.80
        and spearman is not None and spearman >= 0.80
    )

    out = {
        'year': 2020,
        'purpose': 'Paired-series structural reproducibility test: can legacy shareholder-report holdings reconstruct the same breadth-ranked universe as N-PORT when restricted to the same SEC series IDs? No prices, returns, trades, or strategy performance are used.',
        'scopeWarning': 'This tests parser/issuer-identity/universe-score reproducibility on the shared-series subset. It does not prove full historical ETF-registrant coverage parity.',
        'mappingRule': 'Legacy issuer description may map to a symbol only when the nearest same-series N-PORT snapshot has exactly one symbol for the same conservatively normalized issuer name.',
        'universeRule': 'Same production rule: etfCount>=2 OR maxWeight>=4; score=3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight); recency=exp(-ageDays/120).',
        'asOf': as_of,
        'pairedSeries': len(paired),
        'medianLegacySymbolWeightCoverage': median_cov,
        'legacyEligibleSymbols': len(legacy_ranked),
        'nportEligibleSymbols': len(nport_ranked),
        'topN': TOP_N,
        'topOverlapCount': len(common),
        'topOverlapRate': overlap_rate,
        'topJaccard': jaccard,
        'commonTopRankCorrelation': spearman,
        'acceptanceThresholds': {'minimumPairedSeries':10,'minimumMedianLegacySymbolWeightCoverage':0.80,'minimumTopOverlapRate':0.80,'minimumCommonTopRankCorrelation':0.80},
        'pairedSeriesGatePass': gate,
        'legacyTop': legacy_top,
        'nportTop': nport_top,
        'seriesDiagnostics': series_diag,
        'filingDiagnostics': filing_diag,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({k:v for k,v in out.items() if k not in {'legacyTop','nportTop','seriesDiagnostics','filingDiagnostics'}}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
