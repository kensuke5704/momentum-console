#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARD_DIR = ROOT / 'data/research/marketwide-series-class-shards-q1-2006'
OUT = ROOT / 'data/research/sec-marketwide-series-class-merged-q1-2006.json'
EXPECTED_INVENTORY_COUNT = 1480
EXPECTED_SHARD_COUNT = 12
INVENTORY_ARTIFACT_ID = 9945162305


def main():
    paths = sorted(glob.glob(str(SHARD_DIR / '*.json')))
    if len(paths) != EXPECTED_SHARD_COUNT:
        raise RuntimeError(f'expected {EXPECTED_SHARD_COUNT} shard files, found {len(paths)}')

    shards = [json.loads(Path(path).read_text()) for path in paths]
    shard_indexes = sorted(int(s['shardIndex']) for s in shards)
    if shard_indexes != list(range(EXPECTED_SHARD_COUNT)):
        raise RuntimeError(f'unexpected shard indexes: {shard_indexes}')
    if any(int(s['fullInventoryCount']) != EXPECTED_INVENTORY_COUNT for s in shards):
        raise RuntimeError('full inventory count drift across shards')
    if any(int(s['inventoryArtifactId']) != INVENTORY_ARTIFACT_ID for s in shards):
        raise RuntimeError('inventory artifact drift across shards')

    filings = [r for shard in shards for r in shard['results']]
    accession_counts = Counter(r['accession'] for r in filings)
    duplicates = sorted(k for k, count in accession_counts.items() if count != 1)
    if len(filings) != EXPECTED_INVENTORY_COUNT or duplicates:
        raise RuntimeError(
            f'inventory merge mismatch filings={len(filings)} duplicates={len(duplicates)}'
        )

    filings.sort(key=lambda r: (r['dateFiled'], r['cik'], r['accession'], r['form']))
    successful = [r for r in filings if r['fetchStatus'] == 'SUCCESS']
    failed = [r for r in filings if r['fetchStatus'] != 'SUCCESS']
    with_pairs = [r for r in successful if r.get('seriesClassCount', 0) > 0]
    pair_occurrences = []
    for filing in filings:
        for pair in filing.get('pairs', []):
            pair_occurrences.append({
                'accession': filing['accession'],
                'cik': filing['cik'],
                'company': filing['company'],
                'form': filing['form'],
                'dateFiled': filing['dateFiled'],
                **pair,
            })

    series_ids = sorted({p['seriesId'] for p in pair_occurrences})
    class_ids = sorted({p['classId'] for p in pair_occurrences})
    tickers = sorted({p['ticker'] for p in pair_occurrences if p['ticker']})
    series_by_id = defaultdict(lambda: {'names': set(), 'classIds': set(), 'tickers': set(), 'accessions': set(), 'ciks': set()})
    class_by_id = defaultdict(lambda: {'seriesIds': set(), 'names': set(), 'tickers': set(), 'accessions': set(), 'ciks': set()})
    for p in pair_occurrences:
        s = series_by_id[p['seriesId']]
        if p.get('seriesName'):
            s['names'].add(p['seriesName'])
        s['classIds'].add(p['classId'])
        if p.get('ticker'):
            s['tickers'].add(p['ticker'])
        s['accessions'].add(p['accession'])
        s['ciks'].add(p['cik'])
        c = class_by_id[p['classId']]
        c['seriesIds'].add(p['seriesId'])
        if p.get('className'):
            c['names'].add(p['className'])
        if p.get('ticker'):
            c['tickers'].add(p['ticker'])
        c['accessions'].add(p['accession'])
        c['ciks'].add(p['cik'])

    series_catalog = [
        {
            'seriesId': sid,
            'names': sorted(v['names']),
            'classIds': sorted(v['classIds']),
            'tickers': sorted(v['tickers']),
            'accessions': sorted(v['accessions']),
            'ciks': sorted(v['ciks']),
        }
        for sid, v in sorted(series_by_id.items())
    ]
    class_catalog = [
        {
            'classId': cid,
            'seriesIds': sorted(v['seriesIds']),
            'names': sorted(v['names']),
            'tickers': sorted(v['tickers']),
            'accessions': sorted(v['accessions']),
            'ciks': sorted(v['ciks']),
        }
        for cid, v in sorted(class_by_id.items())
    ]
    class_conflicts = [
        row for row in class_catalog
        if len(row['seriesIds']) > 1 or len(row['tickers']) > 1
    ]
    transport_counts = Counter(r.get('transport') or 'ERROR' for r in filings)

    out = {
        'purpose': (
            'Merge all deterministic shards of the fixed 2006-Q1 market-wide N-Q/N-Q-A filing '
            'inventory. This is source discovery only: no known Production registrants/accessions, '
            'holdings content, ranks, returns, or strategy outcomes are used to select filings or '
            'Series/Class rows. Ticker is preserved as filing-time SEC metadata when present, while '
            'no-ticker classes remain in the catalog.'
        ),
        'inventoryArtifactId': INVENTORY_ARTIFACT_ID,
        'shardCount': EXPECTED_SHARD_COUNT,
        'filingCount': len(filings),
        'uniqueRegistrantCikCount': len({r['cik'] for r in filings}),
        'fetchSuccessCount': len(successful),
        'fetchErrorCount': len(failed),
        'filingsWithSeriesClassCount': len(with_pairs),
        'registrantCiksWithSeriesClassCount': len({r['cik'] for r in with_pairs}),
        'pairOccurrenceCount': len(pair_occurrences),
        'uniqueSeriesCount': len(series_ids),
        'uniqueClassCount': len(class_ids),
        'classOccurrencesWithTickerCount': sum(bool(p['ticker']) for p in pair_occurrences),
        'uniqueTickerCount': len(tickers),
        'transportCounts': dict(transport_counts),
        'classMetadataConflictCount': len(class_conflicts),
        'failedAccessions': [
            {
                'accession': r['accession'],
                'cik': r['cik'],
                'company': r['company'],
                'form': r['form'],
                'dateFiled': r['dateFiled'],
                'error': r.get('error'),
            }
            for r in failed
        ],
        'classMetadataConflicts': class_conflicts,
        'tickers': tickers,
        'seriesCatalog': series_catalog,
        'classCatalog': class_catalog,
        'pairOccurrences': pair_occurrences,
        'filings': filings,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print('SUMMARY', json.dumps({
        k: v for k, v in out.items()
        if k not in {
            'failedAccessions', 'classMetadataConflicts', 'tickers', 'seriesCatalog',
            'classCatalog', 'pairOccurrences', 'filings'
        }
    }), flush=True)
    print('TICKER_SAMPLE', json.dumps(tickers[:100]), flush=True)
    print('FAILED_SAMPLE', json.dumps(out['failedAccessions'][:20]), flush=True)


if __name__ == '__main__':
    main()
