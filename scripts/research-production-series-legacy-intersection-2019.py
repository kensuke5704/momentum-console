#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
import math
import tempfile
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'production-series-legacy-intersection-2019.json'
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent': 'momentum-console research kensuke5704@users.noreply.github.com', 'Accept': '*/*'}
TARGET_FORMS = {'N-Q', 'N-Q/A', 'N-CSR', 'N-CSR/A', 'N-CSRS', 'N-CSRS/A'}
DAY_DECAY = 120.0
TOP_N = 80

mspec = importlib.util.spec_from_file_location('meta', ROOT / 'scripts' / 'research-nq-series-metadata-2006.py')
meta = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(meta)


def download_index(path: Path) -> None:
    req = urllib.request.Request(DRIVE, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
        while True:
            b = r.read(1024 * 1024)
            if not b:
                break
            f.write(b)


def index_2019() -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / 'master.zip'
        download_index(zp)
        out = []
        with zipfile.ZipFile(zp) as z:
            qfiles = [n for n in z.namelist() if any(f'master_2019_QTR{q}.idx' in n for q in range(1, 5))]
            for name in sorted(qfiles):
                text = z.read(name).decode('latin-1', 'replace')
                for line in text.splitlines():
                    p = line.split('|')
                    if len(p) < 5:
                        continue
                    cik, company, form, filed, filename = [x.strip() for x in p[:5]]
                    if form.upper() in TARGET_FORMS and filed.startswith('2019-'):
                        out.append({'cik': cik, 'company': company, 'form': form.upper(), 'dateFiled': filed, 'filename': filename})
        return out


def production_2020_rows() -> list[dict]:
    with gzip.open(BOOT, 'rt', encoding='utf-8') as f:
        bp = json.load(f)
    return [x for x in (bp.get('snapshots') or bp.get('filings') or []) if str(x.get('reportDate') or '').startswith('2020')]


def latest_public(rows: list[dict], as_of: str, allowed: set[str] | None = None) -> list[dict]:
    latest = {}
    for x in rows:
        sid = str(x.get('seriesId') or '')
        filed = str(x.get('filingDate') or '')
        if not sid or not filed or filed > as_of:
            continue
        if allowed is not None and sid not in allowed:
            continue
        prev = latest.get(sid)
        if prev is None or (filed, str(x.get('accession') or '')) > (str(prev.get('filingDate') or ''), str(prev.get('accession') or '')):
            latest[sid] = x
    return list(latest.values())


def score(rows: list[dict], as_of: str) -> list[dict]:
    agg = {}
    for f in rows:
        age = max(0, (date.fromisoformat(as_of) - date.fromisoformat(str(f.get('filingDate') or as_of))).days)
        rec = math.exp(-age / DAY_DECAY)
        sid = str(f.get('seriesId') or '')
        for h in f.get('holdings', []):
            sym = str(h.get('symbol') or '').strip().upper()
            w = float(h.get('weight') or 0)
            if not sym or w <= 0:
                continue
            r = agg.setdefault(sym, {'series': set(), 'aggregateWeight': 0.0, 'maxWeight': 0.0, 'recencyWeight': 0.0})
            r['series'].add(sid); r['aggregateWeight'] += w; r['maxWeight'] = max(r['maxWeight'], w); r['recencyWeight'] += w * rec
    out = []
    for sym, r in agg.items():
        n = len(r['series'])
        if not (n >= 2 or r['maxWeight'] >= 4):
            continue
        us = 3 * math.log1p(n) + .5 * math.log1p(r['aggregateWeight']) + .5 * math.log1p(r['recencyWeight'])
        out.append({'symbol': sym, 'score': us, 'etfCount': n})
    out.sort(key=lambda x: (-x['score'], -x['etfCount'], x['symbol']))
    for i, r in enumerate(out, 1): r['rank'] = i
    return out


def corr(a: dict[str, int], b: dict[str, int], common: set[str]) -> float | None:
    if len(common) < 3: return None
    xs = [a[s] for s in sorted(common)]; ys = [b[s] for s in sorted(common)]
    mx = sum(xs)/len(xs); my = sum(ys)/len(ys)
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den = math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    return num/den if den else None


def compare(a: list[dict], b: list[dict]) -> dict:
    at = a[:TOP_N]; bt = b[:TOP_N]
    A = {x['symbol'] for x in at}; B = {x['symbol'] for x in bt}; common = A & B
    ar = {x['symbol']:x['rank'] for x in at}; br = {x['symbol']:x['rank'] for x in bt}
    denom = min(TOP_N, len(at), len(bt))
    top2 = [x['symbol'] for x in at[:2]]
    return {
        'topOverlapCount': len(common),
        'topOverlapRate': len(common)/denom if denom else None,
        'commonTopRankCorrelation': corr(ar, br, common),
        'fullTop2Symbols': top2,
        'fullTop2RetentionRate': sum(s in B for s in top2)/len(top2) if top2 else None,
    }


def main() -> None:
    legacy = index_2019()
    by_cik = defaultdict(list)
    for x in legacy: by_cik[x['cik']].append(x)
    # One latest filing per CIK is sufficient for the series-identity inventory.
    # Selection is date-only and independent of parser success/universe results.
    chosen = [max(rows, key=lambda x: (x['dateFiled'], x['filename'])) for rows in by_cik.values()]
    chosen.sort(key=lambda x: (x['dateFiled'], x['cik']))

    prod = production_2020_rows()
    prod_ids = {str(x.get('seriesId') or '') for x in prod if x.get('seriesId')}
    discovered = set(); eligible_discovered = set(); diagnostics = []
    for i, x in enumerate(chosen, 1):
        try:
            method, text = meta.fetch_prefix(meta.sec_url(x['filename']))
            series = meta.parse_series_contracts(text, x['company'])
            ids = {str(s.get('seriesId') or '') for s in series if s.get('seriesId')}
            eligible = {str(s.get('seriesId') or '') for s in series if s.get('seriesId') and s.get('productionSeriesNameEligible')}
            discovered |= ids; eligible_discovered |= eligible
            hit = eligible & prod_ids
            if hit:
                diagnostics.append({'cik':x['cik'],'company':x['company'],'form':x['form'],'dateFiled':x['dateFiled'],'transport':method,'eligibleSeries':len(eligible),'productionIntersection':len(hit),'intersectionSeriesIds':sorted(hit)})
                print('HIT', i, x['company'][:50], x['form'], 'eligible', len(eligible), 'prodHit', len(hit), flush=True)
        except Exception as e:
            if i % 50 == 0:
                print('FETCH_FAIL', i, repr(e), flush=True)
        if i % 100 == 0:
            print('PROGRESS', i, '/', len(chosen), 'eligibleDiscovered', len(eligible_discovered), 'prodIntersection', len(eligible_discovered & prod_ids), flush=True)
        time.sleep(0.05)

    intersect = eligible_discovered & prod_ids
    as_of = '2020-12-31'
    full = latest_public(prod, as_of)
    restricted = latest_public(prod, as_of, intersect)
    full_rank = score(full, as_of); restricted_rank = score(restricted, as_of)
    cmp = compare(full_rank, restricted_rank)
    out = {
        'purpose': 'Gate-B series-availability bridge: intersect Production 2020 N-PORT series with filing-time Production-eligible series identities found in 2019 legacy N-Q/N-CSR/N-CSRS. No prices/returns/strategy outcomes used.',
        'selectionRule': 'Latest 2019 legacy shareholder report per CIK, chosen by filing date only. Series eligibility exactly matches Production SERIES_NAME ETF/exchange-traded regex.',
        'legacyTargetFilings': len(legacy), 'legacyCikCount': len(chosen),
        'production2020SeriesIds': len(prod_ids),
        'legacyProductionEligibleSeriesIds': len(eligible_discovered),
        'productionSeriesIntersection': len(intersect),
        'productionSeriesIntersectionRate': len(intersect)/len(prod_ids) if prod_ids else None,
        'fullNportLatestSeries': len(full), 'restrictedNportLatestSeries': len(restricted),
        **cmp,
        'metadataGatePass': bool(cmp['topOverlapRate'] is not None and cmp['topOverlapRate'] >= .80 and cmp['commonTopRankCorrelation'] is not None and cmp['commonTopRankCorrelation'] >= .80 and cmp['fullTop2RetentionRate'] is not None and cmp['fullTop2RetentionRate'] >= .90),
        'intersectionSeriesIds': sorted(intersect),
        'hitFilings': diagnostics,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(out, indent=2)+'\n')
    print('SUMMARY', json.dumps({k:v for k,v in out.items() if k not in {'intersectionSeriesIds','hitFilings'}}, sort_keys=True), flush=True)

if __name__ == '__main__': main()
