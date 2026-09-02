#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'fast', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-fast-2020.py'
)
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)
repro = fast.repro

FIXTURE = {
    'company': 'SELECT SECTOR SPDR TRUST',
    'dateFiled': '2020-06-05',
    'filename': 'edgar/data/1064641/0001193125-20-161980.txt',
    'accession': '0001193125-20-161980',
}

STOP = {'THE', 'FUND', 'ETF', 'TRUST', 'SELECT', 'SECTOR', 'SPDR'}


def tokens(s: str) -> set[str]:
    return {x for x in re.findall(r'[A-Z0-9]+', repro.ov.norm_series_text(s)) if x not in STOP}


def sim(a: str, b: str) -> float:
    aa, bb = tokens(a), tokens(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def main() -> None:
    transport, submission = repro.ov.fetch_full_filing(repro.ov.seg.meta.sec_url(FIXTURE['filename']))
    text = repro.ov.embedded_csr(submission)
    series = fast.shared_nport_series_contracts('', FIXTURE['company'])
    spdr = [s for s in series if 'SELECT SECTOR SPDR' in str(s.get('seriesName') or '').upper()]
    blocks = repro.ov.schedule_blocks(text)
    rows = []
    for i, (start, end) in enumerate(blocks):
        raw_context = text[max(0, start - 4000):min(end, start + 1500)]
        visible = ' '.join(repro.ov.visible(raw_context).split())
        normalized = repro.ov.norm_series_text(visible)
        exact = [s for s in spdr if repro.ov.norm_series_text(s.get('seriesName') or '') in normalized]
        ranked = sorted(
            (
                {
                    'seriesId': s.get('seriesId'),
                    'seriesName': s.get('seriesName'),
                    'tokenJaccard': round(sim(visible, s.get('seriesName') or ''), 4),
                }
                for s in spdr
            ),
            key=lambda x: (-x['tokenJaccard'], str(x['seriesName'])),
        )[:5]
        rows.append({
            'block': i,
            'exactMatches': [{'seriesId': s.get('seriesId'), 'seriesName': s.get('seriesName')} for s in exact],
            'topCandidates': ranked,
            'contextTail': visible[-1800:],
        })
    out = {
        'purpose': 'Structural diagnosis of Select Sector SPDR shareholder-report headings versus frozen N-PORT series display names. No prices, returns, ranks, or strategy performance are used.',
        'fixture': FIXTURE,
        'transport': transport,
        'spdrSeriesCount': len(spdr),
        'spdrSeries': [{'seriesId': s.get('seriesId'), 'seriesName': s.get('seriesName')} for s in spdr],
        'scheduleBlocks': len(blocks),
        'rows': rows,
    }
    path = ROOT / 'data' / 'research' / 'spdr-series-heading-diagnostic-2020.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2), flush=True)


if __name__ == '__main__':
    main()
