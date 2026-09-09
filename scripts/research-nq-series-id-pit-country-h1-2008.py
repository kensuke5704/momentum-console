#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'

H1_COUNTRY_RUN_ID = 34104858455
H1_COUNTRY_ARTIFACT_ID = 10012280475
BASE_COUNTRY_ARTIFACT_ID = 9944538015
STRUCTURAL_COUNTRY_ARTIFACT_ID = 9944797581
NPX_BASE_ARTIFACT_ID = 10041975282

MAPPING = DATA / 'nq-series-id-structural-mapping-h1-2008.json'
NPX = DATA / 'npx-pit-master-h1-2008-2008-06.json'
BASE = DATA / 'sec-submission-header-country-full-merged-2006.json'
STRUCT = DATA / 'structural-new-matches-submission-header-country-2006.json'
SHARDS = DATA / 'series-id-country-h1-2008-shards'
COUNTRY_OUT = DATA / 'nq-series-id-country-pit-h1-2008.json'
DIAGNOSTIC_OUT = DATA / 'nq-series-id-country-extension-diagnostic-h1-2008.json'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def record_identity_key(module, row: dict):
    return module.ik(row.get('ticker'), row.get('securityId'))


def configure(module, source_sha: str) -> None:
    module.MAPPING = MAPPING
    module.NPX = NPX
    module.BASE = BASE
    module.STRUCT = STRUCT
    module.SHARDS = SHARDS
    module.COUNTRY_OUT = COUNTRY_OUT
    module.GATE_OUT = DIAGNOSTIC_OUT
    module.CATALOG_SHA = source_sha

    original_loadmod = module.loadmod

    def period_loadmod(name, path):
        loaded = original_loadmod(name, path)
        if name == 'flat':
            original_load_master = loaded.base.load_master

            def load_master_through_2008(years):
                return original_load_master(sorted(set(years) | {2007, 2008}))

            loaded.base.load_master = load_master_through_2008
        return loaded

    module.loadmod = period_loadmod

    # Exact frozen unresolved-input semantics, except N-PX issuer variants from the
    # H1-2008 incremental container are exposed only when public/admitted by the
    # row's signal date. Pre-2008 variants are already validated closed evidence.
    def unresolved_pit(mapping, npx, base, struct):
        evidence = module.frozen(base, struct)
        npx_by_identity = defaultdict(list)
        for rec in npx.get('records', []):
            if not rec.get('ticker') or not (rec.get('issuer') or rec.get('normalizedIssuer')):
                continue
            npx_by_identity[record_identity_key(module, rec)].append(rec)

        rows = defaultdict(lambda: {'aggregateWeight': 0.0, 'occurrenceCount': 0, 'issuerVariants': set()})
        for snap in mapping['monthSnapshots']:
            signal = snap['asOf']
            for filing in snap['sourceFilings']:
                for h in filing.get('holdings', []):
                    if h.get('legacyAssetSection') != 'COMMON_EQUITY' or h.get('mappingStatus') != 'MATCHED_UNIQUE' or not h.get('mappedTicker'):
                        continue
                    if module.static_country(h, signal, evidence)[0] != 'UNKNOWN':
                        continue
                    key = record_identity_key(module, {'ticker': h.get('mappedTicker'), 'securityId': h.get('mappedSecurityId')})
                    q = rows[(key[0], key[1], signal)]
                    q['aggregateWeight'] += float(h.get('weight') or 0)
                    q['occurrenceCount'] += 1
                    for rec in npx_by_identity.get(key, []):
                        fd = rec.get('sourceFilingDate')
                        admitted = rec.get('admittedAtSignal')
                        if isinstance(fd, str) and fd.startswith('2008-'):
                            if fd > signal or (isinstance(admitted, str) and admitted > signal):
                                continue
                        issuer = rec.get('issuer') or rec.get('normalizedIssuer')
                        if issuer:
                            q['issuerVariants'].add(issuer)
                    q['issuerVariants'].add(str(h.get('description') or ''))
        out = []
        for (ticker, sec, signal), row in sorted(rows.items()):
            out.append({'ticker': ticker, 'securityId': sec, 'signalDate': signal, 'aggregateWeight': row['aggregateWeight'], 'occurrenceCount': row['occurrenceCount'], 'issuerVariants': sorted(x for x in row['issuerVariants'] if x)})
        return out

    module.unresolved = unresolved_pit


def issuer_variant_audit(module, mapping: dict, npx: dict, base: dict, struct: dict) -> dict:
    evidence = module.frozen(base, struct)
    npx_by_identity = defaultdict(list)
    incremental = []
    for rec in npx.get('records', []):
        if not rec.get('ticker') or not (rec.get('issuer') or rec.get('normalizedIssuer')):
            continue
        npx_by_identity[record_identity_key(module, rec)].append(rec)
        fd = rec.get('sourceFilingDate')
        if isinstance(fd, str) and fd.startswith('2008-'):
            incremental.append(rec)

    visible = defaultdict(int)
    blocked = defaultdict(int)
    per_signal = defaultdict(lambda: {'identityDates': 0, 'issuerVariants': 0})
    for snap in mapping.get('monthSnapshots', []):
        signal = snap['asOf']
        seen_identity_dates = set()
        variants = set()
        for filing in snap.get('sourceFilings', []):
            for h in filing.get('holdings', []):
                if h.get('legacyAssetSection') != 'COMMON_EQUITY' or h.get('mappingStatus') != 'MATCHED_UNIQUE' or not h.get('mappedTicker'):
                    continue
                if module.static_country(h, signal, evidence)[0] != 'UNKNOWN':
                    continue
                key = record_identity_key(module, {'ticker': h.get('mappedTicker'), 'securityId': h.get('mappedSecurityId')})
                seen_identity_dates.add((key, signal))
                for rec in npx_by_identity.get(key, []):
                    issuer = rec.get('issuer') or rec.get('normalizedIssuer')
                    fd = rec.get('sourceFilingDate')
                    admitted = rec.get('admittedAtSignal')
                    if isinstance(fd, str) and fd.startswith('2008-'):
                        if fd <= signal and (not isinstance(admitted, str) or admitted <= signal):
                            visible[signal] += 1
                            if issuer: variants.add((key, issuer))
                        else:
                            blocked[signal] += 1
                    elif issuer:
                        variants.add((key, issuer))
                desc = str(h.get('description') or '')
                if desc: variants.add((key, desc))
        per_signal[signal] = {'identityDates': len(seen_identity_dates), 'issuerVariants': len(variants)}

    return {
        'incrementalRecordCountInJuneContainer': len(incremental),
        'visibleIssuerVariantOccurrencesBySignal': dict(visible),
        'blockedFutureIssuerVariantOccurrencesBySignal': dict(blocked),
        'perSignalUnresolvedInput': dict(per_signal),
        'rule': 'Pre-2008 validated N-PX issuer variants are eligible throughout H1 2008. A 2008 incremental N-PX issuer variant is visible only when sourceFilingDate <= signalDate and admittedAtSignal <= signalDate. Holding descriptions remain eligible. Future N-PX issuer variants are blocked; frozen country resolution/carry semantics are unchanged.',
    }


def attach_lineage(path: Path, *, diagnostic: bool, source_artifact_id: int, source_sha: str, mapping_run_id: int, mapping_artifact_id: int, npx_run_id: int, npx_artifact_id: int, pit_audit: dict) -> None:
    payload = json.loads(path.read_text())
    payload['purpose'] = (
        'H1 2008 period-extension country sensitivity diagnostic produced by frozen strict PIT country semantics. SEC master-index coverage extends only through 2008 and incremental 2008 N-PX issuer variants are visible only when public by each signal date. This diagnostic does not tune reconstruction or strategy performance.'
        if diagnostic else
        'H1 2008 strict point-in-time country resolution for deterministic mapped COMMON_EQUITY holdings. The authoritative frozen H1 country implementation is reused; SEC master-index coverage extends through 2008 and the only H1-2008-specific adaptation is signal-date filtering of incremental 2008 N-PX issuer-name variants. UNKNOWN remains UNKNOWN.'
    )
    payload['sourceCatalogArtifactId'] = source_artifact_id
    payload['sourceCatalogSha256'] = source_sha
    payload['mappingRunId'] = mapping_run_id
    payload['mappingArtifactId'] = mapping_artifact_id
    payload['authoritativeH1CountryRunId'] = H1_COUNTRY_RUN_ID
    payload['authoritativeH1CountryArtifactId'] = H1_COUNTRY_ARTIFACT_ID
    payload['baseCountryEvidenceArtifactId'] = BASE_COUNTRY_ARTIFACT_ID
    payload['structuralCountryEvidenceArtifactId'] = STRUCTURAL_COUNTRY_ARTIFACT_ID
    payload['npxPitRunId'] = npx_run_id
    payload['npxPitArtifactId'] = npx_artifact_id
    payload['npxBaseArtifactId'] = NPX_BASE_ARTIFACT_ID
    payload['periodExtensionMasterYears'] = [2005, 2006, 2007, 2008]
    payload['npxIssuerVariantPitAudit'] = pit_audit
    path.write_text(json.dumps(payload, indent=2) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('resolve-shard', 'merge'), required=True)
    parser.add_argument('--shard-index', type=int, default=0)
    parser.add_argument('--shard-count', type=int, default=8)
    args = parser.parse_args()

    source_artifact_id = int(os.environ['SOURCE_CATALOG_ARTIFACT_ID'])
    source_sha = os.environ['SOURCE_CATALOG_SHA256'].strip().lower()
    mapping_run_id = int(os.environ['MAPPING_RUN_ID'])
    mapping_artifact_id = int(os.environ['MAPPING_ARTIFACT_ID'])
    npx_run_id = int(os.environ['NPX_PIT_RUN_ID'])
    npx_artifact_id = int(os.environ['NPX_PIT_ARTIFACT_ID'])
    if min(source_artifact_id, mapping_run_id, mapping_artifact_id, npx_run_id, npx_artifact_id) <= 0 or len(source_sha) != 64:
        raise RuntimeError('fixed source/mapping/N-PX lineage environment is invalid')

    module = load_module('authoritative_h1_strict_pit_country', ROOT / 'scripts/research-nq-hybrid-pit-country-gate-b-h1-2006.py')
    configure(module, source_sha)

    if args.mode == 'resolve-shard':
        module.resolve_shard(args)
        return

    module.merge()
    mapping = json.loads(MAPPING.read_text())
    npx = json.loads(NPX.read_text())
    base = json.loads(BASE.read_text())
    struct = json.loads(STRUCT.read_text())
    pit_audit = issuer_variant_audit(module, mapping, npx, base, struct)
    for path, diagnostic in ((COUNTRY_OUT, False), (DIAGNOSTIC_OUT, True)):
        attach_lineage(path, diagnostic=diagnostic, source_artifact_id=source_artifact_id, source_sha=source_sha, mapping_run_id=mapping_run_id, mapping_artifact_id=mapping_artifact_id, npx_run_id=npx_run_id, npx_artifact_id=npx_artifact_id, pit_audit=pit_audit)

    country = json.loads(COUNTRY_OUT.read_text())
    print('H1_2008_COUNTRY_SUMMARY', json.dumps({'sourceCatalogSha256': country.get('catalogSha256'), 'mappingArtifactId': mapping_artifact_id, 'reasonCounts': country.get('reasonCounts'), 'npxIssuerVariantPitAudit': pit_audit, 'monthly': [{'signalMonth': s['signalMonth'], 'sourceSeriesCount': s['sourceSeriesCount'], 'mappedCommonEquityCountryCounts': s.get('mappedCommonEquityCountryCounts'), 'mappedCommonEquityCountryWeights': s.get('mappedCommonEquityCountryWeights'), 'corpPositiveNonCorpNameCount': s.get('corpPositiveNonCorpNameCount')} for s in country.get('monthSnapshots', [])]}), flush=True)


if __name__ == '__main__':
    main()
