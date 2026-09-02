#!/usr/bin/env python3
from __future__ import annotations

import html
import importlib.util
import json
import re
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com', 'Accept': '*/*'}
OUT = ROOT / 'data' / 'research' / 'ishares-nq-table-diagnostic.json'
YEARS = (2008, 2010)
ISHARES = re.compile(r'^I?SHARES\s+(?:TRUST|INC)\b', re.I)

sspec = importlib.util.spec_from_file_location('seg', ROOT / 'scripts' / 'research-nq-series-segmentation-2006.py')
seg = importlib.util.module_from_spec(sspec); sspec.loader.exec_module(seg)
pspec = importlib.util.spec_from_file_location('pit', ROOT / 'scripts' / 'research-nq-pit-holdings-2006.py')
pit = importlib.util.module_from_spec(pspec); pspec.loader.exec_module(pit)

ROW_RE = re.compile(r'(?is)<TR\b[^>]*>(.*?)</TR>')
CELL_RE = re.compile(r'(?is)<T[DH]\b[^>]*>(.*?)</T[DH]>')


def download(path: Path) -> None:
    req = urllib.request.Request(DRIVE, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
        while True:
            b = r.read(1024 * 1024)
            if not b: break
            f.write(b)


def visible(raw: str) -> str:
    s = re.sub(r'(?is)<BR\s*/?>', ' ', raw)
    s = re.sub(r'(?is)<[^>]+>', ' ', s)
    return ' '.join(html.unescape(s).replace('\xa0', ' ').split())


def choose_filings() -> list[dict]:
    chosen = []
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / 'master.zip'; download(zp)
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            for year in YEARS:
                rows = []
                for name in sorted(n for n in names if re.search(rf'master_{year}_QTR[1-4]\.idx$', n)):
                    for line in z.read(name).decode('latin-1', 'replace').splitlines():
                        p = line.split('|')
                        if len(p) < 5: continue
                        cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
                        if form.upper() == 'N-Q' and date_filed.startswith(str(year)) and ISHARES.search(company):
                            rows.append({'year': year, 'cik': cik, 'company': company, 'dateFiled': date_filed, 'filename': filename})
                seen = set()
                for row in sorted(rows, key=lambda r: (r['dateFiled'], r['cik'], r['filename'])):
                    if row['cik'] in seen: continue
                    seen.add(row['cik']); chosen.append(row)
    return chosen


def row_cells(block: str, limit: int = 80) -> list[list[str]]:
    rows = []
    for rm in ROW_RE.finditer(block):
        cells = [visible(x) for x in CELL_RE.findall(rm.group(1))]
        cells = [x for x in cells if x]
        if cells:
            rows.append(cells)
        if len(rows) >= limit:
            break
    return rows


def numeric_tail(cells: list[str]) -> list[str]:
    return [c for c in cells if re.search(r'\d', c)][-4:]


def main() -> None:
    results = []
    for filing in choose_filings():
        try:
            transport, submission = seg.meta.fetch_prefix(seg.meta.sec_url(filing['filename']))
            series = [s for s in seg.meta.parse_series_contracts(submission, filing['company']) if s.get('isEtf') and s.get('seriesId')]
            primary, text = seg.embedded_primary_nq(submission)
            markers = list(seg.SCHEDULE.finditer(text))
            blocks = []
            for j, marker in enumerate(markers):
                start = marker.start(); end = markers[j + 1].start() if j + 1 < len(markers) else min(len(text), start + 300000)
                block = text[start:end]
                context = text[max(0, start - 5000):min(end, start + 2500)]
                mapped, score = seg.map_schedule_to_series(context, series)
                if not mapped: continue
                method, holdings, total = pit.normalized_holdings(block)
                table_rows = row_cells(block)
                likely_data = [r for r in table_rows if len(r) >= 2 and any(re.search(r'\d', c) for c in r[1:])]
                blocks.append({
                    'seriesId': mapped.get('seriesId'), 'seriesName': mapped.get('seriesName'), 'tickers': mapped.get('etfTickers', []),
                    'mappingScore': score, 'oldParserMethod': method, 'oldHoldingCount': len(holdings), 'oldParsedTotal': total,
                    'htmlRowCount': len(table_rows), 'likelyDataRowCount': len(likely_data),
                    'firstRows': table_rows[:18],
                    'numericTails': [numeric_tail(r) for r in likely_data[:18]],
                    'visiblePrefix': visible(block[:12000])[:3000],
                })
            result = {**filing, 'transport': transport, 'primaryDocument': primary, 'registeredEtfSeries': len(series), 'scheduleMarkers': len(markers), 'blocks': blocks}
            print(f"{filing['year']} {filing['company']} series={len(series)} schedules={len(markers)} mapped={len(blocks)}", flush=True)
            for b in blocks[:8]:
                print('BLOCK', json.dumps({k:v for k,v in b.items() if k not in {'firstRows','numericTails','visiblePrefix'}}, ensure_ascii=False), flush=True)
        except Exception as e:
            result = {**filing, 'error': repr(e)}
            print('FAIL', filing['year'], filing['company'], repr(e), flush=True)
        results.append(result)
    out = {
        'purpose': 'Diagnose iShares 2008/2010 N-Q holdings table structure after the legacy parser incorrectly interpreted report-year header values as holdings market values. Structural only; no prices or returns.',
        'selectionRule': 'First N-Q filing per iShares Trust/Inc CIK in deterministic filing order for 2008 and 2010.',
        'results': results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(out, indent=2) + '\n')

if __name__ == '__main__': main()
