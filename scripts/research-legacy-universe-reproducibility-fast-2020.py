#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

TARGET_CIK = '1424212'  # First Trust Exchange-Traded Fund III; predeclared from the 2016 structural anchor sample.


def sec_master_for_cik():
    cik10 = TARGET_CIK.zfill(10)
    url = f'https://data.sec.gov/submissions/CIK{cik10}.json'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    recent = data.get('filings', {}).get('recent', {})
    forms = recent.get('form', [])
    accs = recent.get('accessionNumber', [])
    dates = recent.get('filingDate', [])
    docs = recent.get('primaryDocument', [])
    company = data.get('name') or 'FIRST TRUST EXCHANGE-TRADED FUND III'
    out = []
    for form, acc, filed, doc in zip(forms, accs, dates, docs):
        if form not in {'N-CSR', 'N-CSRS'} or not str(filed).startswith('2020'):
            continue
        acc_digits = str(acc).replace('-', '')
        filename = f'edgar/data/{int(TARGET_CIK)}/{acc_digits}/{doc}'
        out.append({'cik':TARGET_CIK,'company':company,'form':form,'dateFiled':filed,'filename':filename})
    print('SEC_SUBMISSIONS_FILINGS', len(out), [(x['form'],x['dateFiled'],x['filename']) for x in out], flush=True)
    return out


repro.ov.master_2020 = sec_master_for_cik
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'
repro.main()
