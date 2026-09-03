#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / 'efts-legacy-inventory-2019.json'
BASE = 'https://efts.sec.gov/LATEST/search-index'
UA = {
    'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com',
    'Accept': 'application/json',
}
FORMS = 'N-Q,N-CSR,N-CSRS'


def fetch_page(offset: int, size: int = 100) -> dict:
    params = {
        'q': '*',
        'dateRange': 'custom',
        'startdt': '2019-01-01',
        'enddt': '2019-12-31',
        'forms': FORMS,
        'from': str(offset),
        'size': str(size),
    }
    url = BASE + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> None:
    first = fetch_page(0)
    hits_obj = first.get('hits') or {}
    total_obj = hits_obj.get('total') or 0
    total = int(total_obj.get('value') or 0) if isinstance(total_obj, dict) else int(total_obj or 0)
    rows = []
    offset = 0
    while True:
        page = first if offset == 0 else fetch_page(offset)
        hits = ((page.get('hits') or {}).get('hits') or [])
        if not hits:
            break
        for h in hits:
            src = h.get('_source') or {}
            rows.append({
                'id': h.get('_id'),
                'entityName': src.get('entity_name'),
                'form': src.get('form_type'),
                'fileDate': src.get('file_date'),
                'periodOfReport': src.get('period_of_report'),
                'ciks': src.get('ciks'),
                'fileNum': src.get('file_num'),
                'rootForms': src.get('root_forms'),
            })
        offset += len(hits)
        print('PAGE', offset, '/', total, flush=True)
        if offset >= total or len(hits) < 100:
            break
        if offset >= 10000:
            raise RuntimeError('Unexpectedly large EFTS result; refusing to page beyond 10k without explicit redesign')

    forms = {}
    for r in rows:
        f = str(r.get('form') or '')
        forms[f] = forms.get(f, 0) + 1
    out = {
        'purpose': 'Official SEC EFTS structural inventory for 2019 legacy shareholder reports. No prices, returns, holdings outcomes, or strategy performance used.',
        'endpoint': BASE,
        'query': {'forms': FORMS, 'startdt': '2019-01-01', 'enddt': '2019-12-31'},
        'reportedTotal': total,
        'retrievedHits': len(rows),
        'formCounts': dict(sorted(forms.items())),
        'sample': rows[:20],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print('SUMMARY', json.dumps({k: v for k, v in out.items() if k != 'sample'}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
