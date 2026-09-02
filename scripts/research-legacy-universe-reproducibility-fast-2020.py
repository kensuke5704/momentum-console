#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

# Frozen structural fixture. This accession was selected because the registrant is a
# multi-series ETF trust with a June 30, 2020 shareholder report and therefore gives
# the legacy parser enough same-date series to exercise the reproducibility gates.
# Selection uses no prices, returns, ranks, parser-success feedback, or strategy output.
# dateFiled is a deterministic fallback used only by the harness; same-series pairing
# is anchored on CONFORMED PERIOD OF REPORT parsed from the filing itself.
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


repro.ov.master_2020 = fixed_fixture_sample
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'
repro.main()
