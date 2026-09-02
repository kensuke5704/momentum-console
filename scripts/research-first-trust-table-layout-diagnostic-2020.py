#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fast', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-fast-2020.py')
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)

fixture = {
    'company': 'First Trust Exchange-Traded Fund VI',
    'filename': 'edgar/data/1552740/0001445546-20-005815.txt',
}
transport, submission = fast.repro.ov.fetch_full_filing(fast.repro.ov.seg.meta.sec_url(fixture['filename']))
text = fast.repro.ov.embedded_csr(submission)
series = fast.shared_nport_series_contracts('', fixture['company'])
target = 'S000053943'
rows_out = []
for start, end in fast.repro.ov.schedule_blocks(text):
    context = fast.repro.ov.norm_series_text(fast.repro.ov.visible(text[max(0,start-10000):min(end,start+3000)]))
    exact = [s for s in series if fast.repro.ov.norm_series_text(s.get('seriesName') or '') in context]
    if len(exact) != 1 or exact[0]['seriesId'] != target:
        continue
    block = text[start:end]
    table_rows = fast.repro.ov.pit.legacy_holdings.rows(block)
    rows_out.append({
        'seriesId': target,
        'seriesName': exact[0]['seriesName'],
        'rowCount': len(table_rows),
        'rows': table_rows[:40],
    })

out = {'transport': transport, 'blocks': rows_out}
path = ROOT / 'data' / 'research' / 'first-trust-table-layout-diagnostic-2020.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2), flush=True)
