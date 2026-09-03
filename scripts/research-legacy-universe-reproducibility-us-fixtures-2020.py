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

# Load an independent copy of the SEC filing-time series parser. The fast wrapper
# replaces its own parser with frozen N-PORT names; that is useful as a fallback,
# but some valid legacy ETF families (notably Select Sector SPDR) are missing
# seriesName metadata in the frozen bootstrap. Filing <SERIES> contracts are the
# authoritative identity source when present.
mspec = importlib.util.spec_from_file_location(
    'filing_meta', ROOT / 'scripts' / 'research-nq-series-metadata-2006.py'
)
filing_meta = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(filing_meta)

_frozen_series_contracts = fast.shared_nport_series_contracts


def filing_preferred_series_contracts(submission: str, company: str):
    filing_series = [
        s for s in filing_meta.parse_series_contracts(submission, company)
        if s.get('seriesId') and s.get('seriesName') and s.get('isEtf')
    ]
    if filing_series:
        print('FILING_TIME_SERIES_IDENTITIES', len(filing_series), company, flush=True)
        return filing_series
    print('FILING_TIME_SERIES_IDENTITIES 0; FALLBACK_FROZEN_NPORT', company, flush=True)
    return _frozen_series_contracts(submission, company)


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

fast.repro.ov.seg.meta.parse_series_contracts = filing_preferred_series_contracts
fast.repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-us-fixtures-2020.json'
fast.repro.main()
