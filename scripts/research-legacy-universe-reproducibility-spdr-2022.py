#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
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

_frozen_series_contracts = fast.shared_nport_series_contracts


def filing_preferred_series_contracts(submission: str, company: str):
    filing_series = [
        s for s in filing_meta.parse_series_contracts(submission, company)
        if s.get('seriesId') and s.get('seriesName') and s.get('isEtf')
    ]
    if filing_series:
        print('FILING_TIME_SERIES_IDENTITIES', len(filing_series), company, flush=True)
        return filing_series
    return _frozen_series_contracts(submission, company)


# Structurally selected fixture: the full Select Sector SPDR Trust annual report
# with report date 2022-09-30. The frozen N-PORT bootstrap contains same-series
# snapshots at exactly 2022-09-30, unlike its incomplete 2020 SPDR coverage.
# Selection uses SEC registrant/report identity only; no prices, returns, strategy
# ranks, parser-success feedback, or backtest output enter the choice.
fast.FIXTURE_FILINGS = (
    {
        'cik': '1064641',
        'company': 'SELECT SECTOR SPDR TRUST',
        'form': 'N-CSR',
        'dateFiled': '2022-12-07',
        'filename': 'edgar/data/1064641/000119312522300047/0001193125-22-300047.txt',
        'accession': '0001193125-22-300047',
        'fixtureBasis': 'SEC N-CSR for report period 2022-09-30; eleven US sector-equity SPDR funds with exact-date frozen N-PORT coverage',
    },
)

fast.repro.ov.seg.meta.parse_series_contracts = filing_preferred_series_contracts
fast.repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-spdr-2022.json'
fast.repro.main()

# Correct metadata inherited from the generic evaluator; the numerical gates are
# unchanged. This patch only labels the validation period and its structural scope.
out = json.loads(fast.repro.OUT.read_text())
out['year'] = 2022
out['validationFixture'] = {
    'accession': '0001193125-22-300047',
    'reportDate': '2022-09-30',
    'registrant': 'SELECT SECTOR SPDR TRUST',
    'basis': 'Exact same-series report-date overlap with frozen N-PORT bootstrap.',
}
fast.repro.OUT.write_text(json.dumps(out, indent=2) + '\n')
