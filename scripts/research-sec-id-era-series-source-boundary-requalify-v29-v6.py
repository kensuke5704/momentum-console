#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get('POSTID_INPUT_PATH', str(ROOT/'data/research/sec-id-era-strict-series-source-h1-2006-v29qualified.json')))
OUT = Path(os.environ.get('POSTID_OUTPUT_PATH', str(ROOT/'data/research/sec-id-era-strict-series-source-h1-2006-v29boundary-v6.json')))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


grouping = load('grouping_v29_v3', ROOT/'scripts/research-nq-hybrid-grouping-v29-v3.py')
hybrid = grouping.hybrid


def filing_key(row: dict) -> tuple[str, str, str]:
    return (str(row.get('cik') or '').zfill(10), row.get('accession') or '', row.get('filename') or '')


def main() -> None:
    data = json.loads(SRC.read_text())
    occurrences = data.get('sourceOccurrences', [])
    by_filing: dict[tuple[str,str,str], list[dict]] = defaultdict(list)
    for row in occurrences:
        by_filing[filing_key(row)].append(row)

    keep_pairs: set[tuple[tuple[str,str,str],str]] = set()
    audit = []
    fetch_errors = 0
    assignment_rule_counts = Counter()

    for index, (key, rows) in enumerate(sorted(by_filing.items()), 1):
        first = rows[0]
        rec = {
            'cik': key[0], 'accession': key[1], 'filename': key[2],
            'form': first.get('form'), 'dateFiled': first.get('dateFiled'),
            'candidateSeriesIds': sorted({r.get('seriesId') for r in rows if r.get('seriesId')}),
        }
        try:
            submission, transport, attempts = hybrid.fetch_submission(first['filename'])
            rec['transport'] = transport
            rec['transportAttempts'] = attempts
            primary, description, primary_text, doc_type = hybrid.h2diag.primary_document(submission, first['form'])
            rec['primaryDocument'] = primary
            rec['primaryDocumentType'] = doc_type
            rec['documentDescription'] = description
            registrant = first.get('company') or first.get('registrant') or ''
            all_series = hybrid.seg.meta.parse_series_contracts(submission, registrant)
            grouped, assignment_audit = grouping.series_grouped_schedule_blocks(primary_text, all_series)
            for a in assignment_audit:
                assignment_rule_counts[a.get('assignmentRule') or 'UNKNOWN'] += 1
            grouped_ids = set(grouped)
            candidate_ids = set(rec['candidateSeriesIds'])
            qualified = sorted(candidate_ids & grouped_ids)
            missing = sorted(candidate_ids - grouped_ids)
            rec.update({
                'registeredSeriesCount': len(all_series),
                'scheduleMarkerCount': len(assignment_audit),
                'groupedSeriesIds': sorted(grouped_ids),
                'qualifiedSeriesIds': qualified,
                'missingSeriesIds': missing,
                'summaryRejectedMarkerCount': sum(a.get('assignmentRule') == 'SUMMARY_SCHEDULE_NOT_COMPLETE_PORTFOLIO_BLOCK' for a in assignment_audit),
            })
            for sid in qualified:
                keep_pairs.add((key, sid))
        except Exception as exc:
            fetch_errors += 1
            rec['error'] = type(exc).__name__
            rec['errorDetail'] = str(exc)[:1200]
        audit.append(rec)
        print('BOUNDARY_FILING', json.dumps({k:rec.get(k) for k in ('accession','form','candidateSeriesIds','qualifiedSeriesIds','missingSeriesIds','error')}), flush=True)

    kept = [r for r in occurrences if (filing_key(r), r.get('seriesId')) in keep_pairs]
    removed = [r for r in occurrences if (filing_key(r), r.get('seriesId')) not in keep_pairs]

    # Rebuild PIT monthly snapshots from only occurrences whose final deterministic
    # portfolio-schedule boundary contains that exact Series ID. Latest qualifying
    # filing on or before each as-of date wins; no holdings content is consulted.
    snapshots = []
    for old in data.get('monthSnapshots', []):
        asof = old['asOf']
        latest = {}
        for row in kept:
            filed = row.get('dateFiled')
            sid = row.get('seriesId')
            if not sid or not filed or filed > asof:
                continue
            prev = latest.get(sid)
            if prev is None or (filed, row.get('accession') or '') > (prev.get('dateFiled') or '', prev.get('accession') or ''):
                latest[sid] = row
        source_filings = []
        for sid, row in sorted(latest.items()):
            source_filings.append({
                'seriesId': sid,
                'seriesName': row.get('seriesName'),
                'cik': str(row.get('cik') or '').zfill(10),
                'registrant': row.get('company') or row.get('registrant'),
                'form': row.get('form'),
                'filingDate': row.get('dateFiled'),
                'accession': row.get('accession'),
                'filename': row.get('filename'),
                'evidenceDateFiled': row.get('evidenceDateFiled'),
                'binding': row.get('binding'),
            })
        snapshots.append({'signalMonth':old['signalMonth'],'asOf':asof,'sourceSeriesCount':len(source_filings),'sourceFilings':source_filings})
        print('BOUNDARY_MONTH', json.dumps({'signalMonth':old['signalMonth'],'sourceSeriesCount':len(source_filings)}), flush=True)

    out = dict(data)
    out.update({
        'purpose': (
            'Post-ID H1 2006 source catalog requalified with the same final deterministic Series-boundary grouping '
            'used by authoritative holdings extraction. Registration metadata alone never proves a holdings source. '
            'A Series/filing occurrence survives only when that exact Series ID owns at least one non-summary '
            'Schedule-of-Investments block in the primary filing document. No ticker, holdings content, fuzzy '
            'matching, return, rank or strategy outcome is used.'
        ),
        'sourceOccurrenceQualificationRule': 'FINAL_V29_V3_EXACT_SERIES_BOUNDARY_NON_SUMMARY_BLOCK_REQUIRED',
        'preBoundarySourceOccurrenceCount': len(occurrences),
        'sourceOccurrenceCount': len(kept),
        'boundaryRemovedSourceOccurrenceCount': len(removed),
        'boundaryRemovedSeriesAccessionPairs': [
            {'seriesId':r.get('seriesId'),'seriesName':r.get('seriesName'),'accession':r.get('accession'),'filename':r.get('filename'),'dateFiled':r.get('dateFiled')}
            for r in removed
        ],
        'boundaryQualificationFetchErrorCount': fetch_errors,
        'boundaryAssignmentRuleCounts': dict(assignment_rule_counts),
        'sourceOccurrences': kept,
        'monthSnapshots': snapshots,
        'boundaryQualificationAudit': audit,
    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2)+'\n')
    print('BOUNDARY_SUMMARY', json.dumps({
        'preSourceOccurrenceCount':len(occurrences), 'sourceOccurrenceCount':len(kept),
        'removedSourceOccurrenceCount':len(removed), 'fetchErrorCount':fetch_errors,
        'removedPairs':out['boundaryRemovedSeriesAccessionPairs']
    }), flush=True)
    if fetch_errors:
        raise SystemExit(f'boundary requalification fetch errors: {fetch_errors}')

if __name__ == '__main__':
    main()
