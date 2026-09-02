#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Load the existing frozen-fixture wrapper first so this validation uses exactly the
# same hybrid legacy parser and structural gates.
spec = importlib.util.spec_from_file_location(
    'fast_repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-fast-2020.py'
)
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)

# Predeclared structural fixtures. Selection is based only on SEC registrant/report
# identity and the frozen N-PORT inventory showing non-empty Production-filtered
# US/CORP/EC holdings at the same report dates. No price, return, strategy rank,
# parser-success feedback, or backtest result is used.
fast.FIXTURE_FILINGS = (
    {
        'cik': '1329377',
        'company': 'First Trust Exchange-Traded Fund',
        'form': 'N-CSR',
        'dateFiled': '2020-03-05',
        'filename': 'edgar/data/1329377/0001445546-20-001301.txt',
        'accession': '0001445546-20-001301',
        'fixtureBasis': 'SEC shareholder report for 2019-12-31; multi-series US-equity ETF trust',
    },
    {
        'cik': '1064641',
        'company': 'SELECT SECTOR SPDR TRUST',
        'form': 'N-CSRS',
        'dateFiled': '2020-06-05',
        'filename': 'edgar/data/1064641/0001193125-20-161980.txt',
        'accession': '0001193125-20-161980',
        'fixtureBasis': 'SEC N-CSRS for report period 2020-03-31; eleven US sector-equity SPDR funds',
    },
    {
        'cik': '1552740',
        'company': 'First Trust Exchange-Traded Fund VI',
        'form': 'N-CSRS',
        'dateFiled': '2020-12-07',
        'filename': 'edgar/data/1552740/0001445546-20-005815.txt',
        'accession': '0001445546-20-005815',
        'fixtureBasis': 'SEC shareholder report for 2020-09-30; four explicit US Equity Select/Dividend ETF series',
    },
)

fast.repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-us-fixtures-2020.json'
fast.repro.main()
