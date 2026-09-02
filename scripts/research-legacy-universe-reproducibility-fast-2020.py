#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

DENSE_FAMILIES = (
    'SELECT SECTOR SPDR',
    'SPDR SERIES TRUST',
    'STREETTRACKS SERIES TRUST',
    'POWERSHARES EXCHANGE TRADED FUND TRUST',
    'INVESCO EXCHANGE-TRADED FUND TRUST',
    'INVESCO EXCHANGE TRADED FUND TRUST',
    'RYDEX ETF TRUST',
)
UA = {'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com', 'Accept': 'text/plain,*/*'}


def dense_index_sample():
    rows = []
    for q in range(1, 5):
        url = f'https://www.sec.gov/Archives/edgar/full-index/2020/QTR{q}/master.idx'
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode('latin-1', 'replace')
        for line in text.splitlines():
            p = line.split('|')
            if len(p) < 5:
                continue
            cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
            if form.upper() not in {'N-CSR', 'N-CSRS'}:
                continue
            company_u = company.upper()
            if any(name in company_u for name in DENSE_FAMILIES):
                rows.append({'cik': cik, 'company': company, 'form': form.upper(), 'dateFiled': date_filed, 'filename': filename})
    print('SEC_DENSE_FILINGS', len(rows), sorted({str(x.get('company') or '') for x in rows}), flush=True)
    return rows


repro.ov.master_2020 = dense_index_sample
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'
repro.main()
