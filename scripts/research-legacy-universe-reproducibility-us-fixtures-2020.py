#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    'fast_repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-fast-2020.py'
)
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)

mspec = importlib.util.spec_from_file_location(
    'filing_meta', ROOT / 'scripts' / 'research-nq-series-metadata-2006.py'
)
filing_meta = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(filing_meta)

ispec = importlib.util.spec_from_file_location(
    'issuer_aliases', ROOT / 'scripts' / 'research-legacy-issuer-aliases.py'
)
issuer_aliases = importlib.util.module_from_spec(ispec)
ispec.loader.exec_module(issuer_aliases)

_frozen_series_contracts = fast.shared_nport_series_contracts
_original_aliases = fast.repro.issuer_aliases


def production_aliases(raw: str):
    return issuer_aliases.issuer_aliases(raw, fast.repro.ov.norm_issuer)


# All alias matches still flow through unique_alias_symbol_map, which accepts an
# alias only when exactly one symbol owns it inside the same N-PORT series.
fast.repro.issuer_aliases = production_aliases


def filing_preferred_series_contracts(submission: str, company: str):
    filing_series = [
        s for s in filing_meta.parse_series_contracts(submission, company)
        if s.get('seriesId') and s.get('seriesName') and s.get('productionSeriesNameEligible')
    ]
    if filing_series:
        print('FILING_TIME_PRODUCTION_SERIES_IDENTITIES', len(filing_series), company, flush=True)
        return filing_series
    print('FILING_TIME_PRODUCTION_SERIES_IDENTITIES 0; FALLBACK_FROZEN_NPORT', company, flush=True)
    return _frozen_series_contracts(submission, company)


# Predeclared structural fixtures. Selection is based only on SEC registrant/report
# identity and broad US-equity ETF-family relevance. No price, return, strategy rank,
# parser-success feedback, or backtest result is used. Exact accession IDs are printed
# so the seriesId intersection can be audited independently of Gate A output.
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
        'cik': '1510337',
        'company': 'First Trust Exchange-Traded AlphaDEX Fund II',
        'form': 'N-CSRS',
        'dateFiled': '2020-08-31',
        'filename': 'edgar/data/1510337/0001445546-20-004251.txt',
        'accession': '0001445546-20-004251',
        'fixtureBasis': 'Predeclared fast-parity fixture; SEC shareholder report for 2020-06-30; multi-series ETF registrant',
    },
    {
        'cik': '1616668',
        'company': 'Pacer Funds Trust',
        'form': 'N-CSR',
        'dateFiled': '2020-07-08',
        'filename': 'edgar/data/1616668/0001398344-20-013455.txt',
        'accession': '0001398344-20-013455',
        'fixtureBasis': 'Predeclared source-coverage family; SEC N-CSR for 2020-04-30 with broad US-equity ETF series set',
    },
    {
        'cik': '1100663',
        'company': 'ISHARES TRUST',
        'form': 'N-CSR',
        'dateFiled': '2020-06-04',
        'filename': 'edgar/data/1100663/0001193125-20-160176.txt',
        'accession': '0001193125-20-160176',
        'fixtureBasis': 'SEC N-CSR for report period 2020-03-31; broad iShares ETF registrant containing US-equity series',
    },
    {
        'cik': '1064641',
        'company': 'SELECT SECTOR SPDR TRUST',
        'form': 'N-CSRS',
        'dateFiled': '2020-06-05',
        'filename': 'edgar/data/1064641/0001193125-20-161980.txt',
        'accession': '0001193125-20-161980',
        'fixtureBasis': 'SEC N-CSRS for report period 2020-03-31; negative control because Production series-name regex excludes the Select Sector names',
    },
    {
        'cik': '1524513',
        'company': 'ISHARES U.S. ETF TRUST',
        'form': 'N-CSRS',
        'dateFiled': '2020-07-02',
        'filename': 'edgar/data/1524513/0001193125-20-186178.txt',
        'accession': '0001193125-20-186178',
        'fixtureBasis': 'SEC N-CSRS for report period 2020-04-30; explicit U.S. ETF registrant retained as structural control',
    },
    {
        'cik': '1552740',
        'company': 'First Trust Exchange-Traded Fund VI',
        'form': 'N-CSRS',
        'dateFiled': '2020-12-07',
        'filename': 'edgar/data/1552740/0001445546-20-005815.txt',
        'accession': '0001445546-20-005815',
        'fixtureBasis': 'SEC shareholder report for 2020-09-30; explicit US Equity Select/Dividend ETF series',
    },
)

print('FIXTURE_ACCESSIONS', [x['accession'] for x in fast.FIXTURE_FILINGS], flush=True)
fast.repro.ov.seg.meta.parse_series_contracts = filing_preferred_series_contracts
fast.repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-us-fixtures-2020.json'
fast.repro.main()
