#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('meta', ROOT / 'scripts' / 'research-nq-series-metadata-2006.py')
meta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(meta)

# These cases encode the exact series-name regex in
# src/lib/universe/nport-quarterly.ts. Registrant/class metadata must not affect
# Production-parity eligibility.
CASES = {
    'ARK Innovation ETF': True,
    'First Trust Nasdaq Semiconductor ETF': True,
    'Example Exchange-Traded Fund': True,
    'Example Exchange Traded Fund': True,
    'The Technology Select Sector SPDR Fund': False,
    'Consumer Discretionary Select Sector SPDR Fund': False,
    'Vanguard 500 Index Fund': False,
    'ETFISH NAME': False,
    'An ETF Portfolio': True,
}

for name, expected in CASES.items():
    actual = meta.production_series_name_eligible(name)
    if actual != expected:
        raise AssertionError(f'{name!r}: expected {expected}, got {actual}')

# Explicitly prove registrant shortcuts remain diagnostic-only.
sgml = '''<SERIES>\n<SERIES-ID>S1\n<SERIES-NAME>The Technology Select Sector SPDR Fund\n<CLASS-CONTRACT>\n<CLASS-CONTRACT-ID>C1\n<CLASS-CONTRACT-NAME>Technology Select Sector SPDR\n<CLASS-CONTRACT-TICKER-SYMBOL>XLK\n</CLASS-CONTRACT>\n</SERIES>'''
row = meta.parse_series_contracts(sgml, 'SELECT SECTOR SPDR TRUST')[0]
assert row['isEtf'] is True
assert row['strongEtfRegistrant'] is True
assert row['productionSeriesNameEligible'] is False

print('PRODUCTION_SERIES_CONTRACT_PARITY_PASS', len(CASES))
