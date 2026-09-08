#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'
H1_SOURCE = DATA / 'sec-id-era-strict-series-source-h1-2007.json'
H2_SOURCE = DATA / 'sec-id-era-strict-series-source-h2-2007.json'
H1_PREF = DATA / 'sec-etf-registrant-operational-prefilter-through-h1-2007.json'
H2_PREF = DATA / 'sec-etf-registrant-operational-prefilter-through-h2-2007.json'
OUT = DATA / 'sec-id-era-strict-series-source-h2-2007-replay-diagnostic.json'
CLOSED_ASOF = '2007-06-29'


def snap(payload: dict, month: str, key: str) -> dict:
    for row in payload.get(key, []):
        if row.get('signalMonth') == month:
            return row
    raise RuntimeError(f'missing {month} in {key}')


def main() -> None:
    h1 = json.loads(H1_SOURCE.read_text())
    h2 = json.loads(H2_SOURCE.read_text())
    h1_pref = json.loads(H1_PREF.read_text())
    h2_pref = json.loads(H2_PREF.read_text())

    left = snap(h1, '2007-06', 'monthSnapshots')
    right = snap(h2, '2007-06', 'closedHistoryReplaySnapshots')
    lby = {r['seriesId']: r for r in left['sourceFilings']}
    rby = {r['seriesId']: r for r in right['sourceFilings']}
    h1_pos = {r['seriesId']: r for r in h1['positiveSeries']}
    h2_pos = {r['seriesId']: r for r in h2['positiveSeries']}
    h1_candidates = set(h1_pref['positiveCiks'])
    h2_candidates = set(h2_pref['positiveCiks'])
    h2_candidate_source = {r['cik']: r.get('candidateSource') for r in h2_pref.get('positiveCandidates', [])}

    extra_ids = sorted(set(rby) - set(lby))
    missing_ids = sorted(set(lby) - set(rby))
    changed_common = []
    for sid in sorted(set(lby) & set(rby)):
        if lby[sid] != rby[sid]:
            changed_common.append({
                'seriesId': sid,
                'h1': lby[sid],
                'h2Replay': rby[sid],
            })

    extras = []
    for sid in extra_ids:
        src = rby[sid]
        pos = h2_pos[sid]
        cik = src['cik']
        if cik not in h1_candidates:
            cause = 'CIK_NOT_IN_H1_CANDIDATE_REVIEW_SET'
        elif sid not in h1_pos:
            cause = 'CIK_WAS_H1_CANDIDATE_BUT_SERIES_NOT_H1_POSITIVE'
        else:
            cause = 'OTHER'
        extras.append({
            'seriesId': sid,
            'seriesName': src.get('seriesName'),
            'cik': cik,
            'registrant': src.get('registrant'),
            'sourceFilingDate': src.get('filingDate'),
            'sourceAccession': src.get('accession'),
            'evidenceDateFiled': src.get('evidenceDateFiled'),
            'binding': src.get('binding'),
            'seriesMetadataFirstDate': pos.get('seriesMetadataFirstDate'),
            'positiveEvidenceDateFiled': pos.get('evidenceDateFiled'),
            'inH1CandidateReviewSet': cik in h1_candidates,
            'inH2CandidateReviewSet': cik in h2_candidates,
            'h2CandidateSource': h2_candidate_source.get(cik),
            'inH1PositiveSeries': sid in h1_pos,
            'causeClass': cause,
        })

    cause_counts = {}
    for row in extras:
        cause_counts[row['causeClass']] = cause_counts.get(row['causeClass'], 0) + 1

    report = {
        'purpose': (
            'Audit-only diagnosis of the pre-defined H2-2007 closed-history replay failure. '
            'It compares the authoritative H1-2007 June source snapshot with the cumulative H2 replay and classifies '
            'extra Series by prior candidate-review membership. It does not change source evidence, binding, identity, '
            'eligibility, country, ranking, or strategy rules.'
        ),
        'closedMonth': '2007-06',
        'closedAsOf': CLOSED_ASOF,
        'h1SourceSeriesCount': left['sourceSeriesCount'],
        'h2ReplaySourceSeriesCount': right['sourceSeriesCount'],
        'extraSeriesCount': len(extra_ids),
        'missingSeriesCount': len(missing_ids),
        'changedCommonSeriesCount': len(changed_common),
        'causeCounts': cause_counts,
        'extraSeries': extras,
        'missingSeriesIds': missing_ids,
        'changedCommonSeries': changed_common,
    }
    OUT.write_text(json.dumps(report, indent=2) + '\n')
    print('H2_2007_REPLAY_DIAGNOSTIC', json.dumps({
        'h1': report['h1SourceSeriesCount'],
        'h2Replay': report['h2ReplaySourceSeriesCount'],
        'extra': report['extraSeriesCount'],
        'missing': report['missingSeriesCount'],
        'changedCommon': report['changedCommonSeriesCount'],
        'causeCounts': report['causeCounts'],
    }, separators=(',', ':')), flush=True)
    for row in extras:
        print('EXTRA', json.dumps(row, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
