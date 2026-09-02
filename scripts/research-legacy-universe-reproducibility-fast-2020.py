#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

# Predeclared high-density ETF families. Selection is structural only; no parser
# success, prices, returns, ranks, or strategy results enter the sample choice.
DENSE_FAMILIES = (
    'SELECT SECTOR SPDR',
    'SPDR SERIES TRUST',
    'STREETTRACKS SERIES TRUST',
    'POWERSHARES EXCHANGE TRADED FUND TRUST',
    'INVESCO EXCHANGE-TRADED FUND TRUST',
    'INVESCO EXCHANGE TRADED FUND TRUST',
    'RYDEX ETF TRUST',
)


def dense_index_sample():
    # Reuse the deterministic SEC master-index inventory already used by the full
    # overlap validation. This avoids data.sec.gov/submissions rate/access behavior
    # changing the research result while preserving exactly the same filing universe.
    filings = repro.ov.master_2020()
    out = []
    for row in filings:
        company = str(row.get('company') or '').upper()
        if any(name in company for name in DENSE_FAMILIES):
            out.append(row)
    print('INDEXED_DENSE_FILINGS', len(out), sorted({str(x.get('company') or '') for x in out}), flush=True)
    return out


repro.ov.master_2020 = dense_index_sample
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'
repro.main()
