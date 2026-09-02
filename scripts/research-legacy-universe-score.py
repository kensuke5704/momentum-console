#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

DAY_DECAY = 120.0
DEFAULT_SIZE = 80


@dataclass(frozen=True)
class Holding:
    symbol: str
    weight: float


@dataclass(frozen=True)
class Filing:
    accession: str
    series_id: str
    series_name: str
    filing_date: str
    holdings: tuple[Holding, ...]


def age_days(as_of: str, filed: str) -> int:
    return max(0, (date.fromisoformat(as_of) - date.fromisoformat(filed)).days)


def latest_public_filings(filings: Iterable[Filing], as_of: str) -> list[Filing]:
    latest: dict[str, Filing] = {}
    for filing in filings:
        if filing.filing_date > as_of:
            continue
        prev = latest.get(filing.series_id)
        if prev is None or (filing.filing_date, filing.accession) > (prev.filing_date, prev.accession):
            latest[filing.series_id] = filing
    return sorted(latest.values(), key=lambda f: (f.series_id, f.filing_date, f.accession))


def build_universe(filings: Iterable[Filing], as_of: str, size: int = DEFAULT_SIZE) -> dict:
    sources = latest_public_filings(filings, as_of)
    rows: dict[str, dict] = {}
    for filing in sources:
        recency_factor = math.exp(-age_days(as_of, filing.filing_date) / DAY_DECAY)
        for holding in filing.holdings:
            if not (holding.weight > 0):
                continue
            symbol = holding.symbol.strip().upper()
            if not symbol:
                continue
            row = rows.setdefault(symbol, {
                'seriesIds': set(),
                'aggregateWeight': 0.0,
                'maxWeight': 0.0,
                'recencyWeight': 0.0,
            })
            row['seriesIds'].add(filing.series_id)
            row['aggregateWeight'] += holding.weight
            row['maxWeight'] = max(row['maxWeight'], holding.weight)
            row['recencyWeight'] += holding.weight * recency_factor

    scored = []
    for symbol, row in rows.items():
        etf_count = len(row['seriesIds'])
        if not (etf_count >= 2 or row['maxWeight'] >= 4):
            continue
        score = (
            3 * math.log1p(etf_count)
            + 0.5 * math.log1p(row['aggregateWeight'])
            + 0.5 * math.log1p(row['recencyWeight'])
        )
        scored.append({
            'symbol': symbol,
            'etfCount': etf_count,
            'aggregateWeight': row['aggregateWeight'],
            'maxWeight': row['maxWeight'],
            'recencyWeight': row['recencyWeight'],
            'universeScore': score,
        })

    scored.sort(key=lambda r: (-r['universeScore'], -r['etfCount'], -r['aggregateWeight'], r['symbol']))
    symbols = [{**row, 'universeRank': i + 1} for i, row in enumerate(scored[:max(0, size)])]
    return {
        'asOf': as_of,
        'size': size,
        'scoringRule': '3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight)',
        'eligibilityRule': 'etfCount >= 2 OR maxWeight >= 4',
        'recencyHalfLifeStyle': 'exp(-ageDays/120), identical functional form to production universe.ts',
        'sourceFilings': [
            {'accession': f.accession, 'seriesId': f.series_id, 'seriesName': f.series_name, 'filingDate': f.filing_date}
            for f in sources
        ],
        'symbols': symbols,
    }


def load_filings(path: Path) -> list[Filing]:
    raw = json.loads(path.read_text())
    source = raw.get('filings', raw if isinstance(raw, list) else [])
    filings = []
    for row in source:
        holdings = tuple(
            Holding(str(h.get('symbol') or '').upper(), float(h.get('weight') or 0.0))
            for h in row.get('holdings', [])
            if h.get('symbol')
        )
        filings.append(Filing(
            accession=str(row.get('accession') or ''),
            series_id=str(row.get('seriesId') or ''),
            series_name=str(row.get('seriesName') or ''),
            filing_date=str(row.get('filingDate') or ''),
            holdings=holdings,
        ))
    return [f for f in filings if f.series_id and f.filing_date]


def self_test() -> None:
    filings = [
        Filing('a1', 'S1', 'Fund 1', '2008-01-10', (Holding('AAA', 5), Holding('BBB', 2))),
        Filing('a2', 'S2', 'Fund 2', '2008-01-20', (Holding('AAA', 3), Holding('CCC', 6))),
        Filing('a3', 'S1', 'Fund 1', '2008-02-10', (Holding('AAA', 1), Holding('DDD', 5))),
    ]
    jan = build_universe(filings, '2008-01-31', 80)
    assert jan['sourceFilings'][0]['accession'] == 'a1'
    jan_map = {x['symbol']: x for x in jan['symbols']}
    assert jan_map['AAA']['etfCount'] == 2
    assert abs(jan_map['AAA']['aggregateWeight'] - 8.0) < 1e-12
    assert 'BBB' not in jan_map  # one ETF and max weight below 4
    assert jan_map['CCC']['maxWeight'] == 6

    feb = build_universe(filings, '2008-02-29', 80)
    accessions = {x['accession'] for x in feb['sourceFilings']}
    assert 'a3' in accessions and 'a1' not in accessions
    feb_map = {x['symbol']: x for x in feb['symbols']}
    assert feb_map['DDD']['maxWeight'] == 5
    print('SELF_TEST_PASS')


def main() -> None:
    ap = argparse.ArgumentParser(description='Legacy SEC-filings universe scorer. This script consumes no prices or returns.')
    ap.add_argument('--input')
    ap.add_argument('--as-of')
    ap.add_argument('--size', type=int, default=DEFAULT_SIZE)
    ap.add_argument('--output')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    if not args.input or not args.as_of:
        raise SystemExit('--input and --as-of are required unless --self-test is used')
    result = build_universe(load_filings(Path(args.input)), args.as_of, args.size)
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
