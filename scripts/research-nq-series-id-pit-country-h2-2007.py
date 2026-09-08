#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"

SOURCE_ARTIFACT_ID = 10041257985
SOURCE_SHA = "9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631"
MAPPING_RUN_ID = 34190421577
MAPPING_ARTIFACT_ID = 10042002365
NPX_PIT_RUN_ID = 34190105652
NPX_PIT_ARTIFACT_ID = 10041975282
NPX_BASE_ARTIFACT_ID = 9876020712
BASE_COUNTRY_ARTIFACT_ID = 9944538015
STRUCTURAL_COUNTRY_ARTIFACT_ID = 9944797581
AUTHORITATIVE_H1_COUNTRY_RUN_ID = 34104858455
AUTHORITATIVE_H1_COUNTRY_ARTIFACT_ID = 10012280475

MAPPING = DATA / "nq-series-id-structural-mapping-h2-2007.json"
NPX = DATA / "npx-pit-master-h2-2007-2007-12.json"
NPX_AUDIT = DATA / "npx-pit-master-h2-2007-audit.json"
BASE = DATA / "sec-submission-header-country-full-merged-2006.json"
STRUCT = DATA / "structural-new-matches-submission-header-country-2006.json"
SHARDS = DATA / "series-id-country-h2-2007-shards"
COUNTRY_OUT = DATA / "nq-series-id-country-pit-h2-2007.json"
DIAGNOSTIC_OUT = DATA / "nq-series-id-country-extension-diagnostic-h2-2007.json"
EXPECTED = [
    ("2007-07", "2007-07-31", 465),
    ("2007-08", "2007-08-31", 469),
    ("2007-09", "2007-09-28", 499),
    ("2007-10", "2007-10-31", 518),
    ("2007-11", "2007-11-30", 531),
    ("2007-12", "2007-12-31", 533),
]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def validate_upstream() -> tuple[dict, dict]:
    mapping = json.loads(MAPPING.read_text())
    npx = json.loads(NPX.read_text())
    audit = json.loads(NPX_AUDIT.read_text())
    if mapping.get("sourceCatalogArtifactId") != SOURCE_ARTIFACT_ID or mapping.get("sourceCatalogSha256") != SOURCE_SHA:
        raise RuntimeError("unexpected H2 source lineage in mapping")
    if mapping.get("holdingsRunId") != 34188353154 or mapping.get("holdingsArtifactId") != 10041300366:
        raise RuntimeError("unexpected H2 holdings lineage in mapping")
    if mapping.get("npxPitRunId") != NPX_PIT_RUN_ID or mapping.get("npxPitArtifactId") != NPX_PIT_ARTIFACT_ID:
        raise RuntimeError("unexpected H2 N-PX lineage in mapping")
    if [(s.get("signalMonth"), s.get("asOf"), s.get("sourceSeriesCount")) for s in mapping.get("monthSnapshots", [])] != EXPECTED:
        raise RuntimeError("unexpected H2 mapping month/source boundary")
    if audit.get("status") != "PASS" or audit.get("fetchErrorCount") != 0 or audit.get("violations"):
        raise RuntimeError("authoritative H2 N-PX audit is not PASS/clean")
    if audit.get("baseArtifactId") != NPX_BASE_ARTIFACT_ID:
        raise RuntimeError("unexpected N-PX frozen-base lineage")
    if npx.get("signalMonth") != "2007-12" or npx.get("asOf") != "2007-12-31":
        raise RuntimeError("country wrapper requires authoritative cumulative December H2 N-PX container")
    if npx.get("baseArtifactId") != NPX_BASE_ARTIFACT_ID:
        raise RuntimeError("unexpected December N-PX base lineage")
    return mapping, npx


def record_public_by_signal(row: dict, signal: str) -> bool:
    filing = row.get("sourceFilingDate")
    admitted = row.get("admittedAtSignal")
    if isinstance(filing, str) and filing.startswith("2007-"):
        if not admitted:
            raise RuntimeError(f"2007 N-PX record lacks admittedAtSignal: {row.get('ticker')} {row.get('securityId')}")
        if admitted > signal or filing > signal:
            return False
        return True
    if admitted:
        # Incremental rows are required to be 2007 records in the authoritative H2 master.
        if not isinstance(filing, str) or not filing.startswith("2007-"):
            raise RuntimeError(f"incremental N-PX row has invalid filing date: filing={filing} admitted={admitted}")
        return admitted <= signal and filing <= signal
    # Frozen pre-2007 base row. Year-level provenance such as "2006" is allowed.
    if isinstance(filing, str) and filing[:4].isdigit() and filing[:4] > "2006":
        raise RuntimeError(f"undated/unadmitted post-2006 N-PX row encountered: {filing}")
    return True


def make_pit_unresolved(module):
    def unresolved(mapping: dict, npx: dict, base: dict, struct: dict):
        evidence = module.frozen(base, struct)
        iv_rows = defaultdict(list)
        incremental_records = 0
        for row in npx.get("records", []):
            if row.get("ticker") and (row.get("issuer") or row.get("normalizedIssuer")):
                key = module.ik(row.get("ticker"), row.get("securityId"))
                name = row.get("issuer") or row.get("normalizedIssuer")
                iv_rows[key].append((row, name))
            if row.get("admittedAtSignal"):
                incremental_records += 1
                filing = row.get("sourceFilingDate")
                admitted = row.get("admittedAtSignal")
                if not (isinstance(filing, str) and filing.startswith("2007-") and isinstance(admitted, str)):
                    raise RuntimeError("incremental H2 N-PX record lacks required PIT dates")
                if filing > admitted:
                    raise RuntimeError(f"N-PX record admitted before filing date: {filing} > {admitted}")

        rows = defaultdict(lambda: {"aggregateWeight": 0.0, "occurrenceCount": 0, "issuerVariants": set()})
        visible_counts = defaultdict(int)
        blocked_counts = defaultdict(int)
        for snap in mapping["monthSnapshots"]:
            signal = snap["asOf"]
            for filing in snap["sourceFilings"]:
                for holding in filing.get("holdings", []):
                    if (
                        holding.get("legacyAssetSection") != "COMMON_EQUITY"
                        or holding.get("mappingStatus") != "MATCHED_UNIQUE"
                        or not holding.get("mappedTicker")
                    ):
                        continue
                    if module.static_country(holding, signal, evidence)[0] != "UNKNOWN":
                        continue
                    key = module.ik(holding.get("mappedTicker"), holding.get("mappedSecurityId"))
                    q = rows[(key[0], key[1], signal)]
                    q["aggregateWeight"] += float(holding.get("weight") or 0)
                    q["occurrenceCount"] += 1
                    for npx_row, issuer_name in iv_rows.get(key, []):
                        if record_public_by_signal(npx_row, signal):
                            q["issuerVariants"].add(issuer_name)
                            visible_counts[signal] += 1
                        else:
                            blocked_counts[signal] += 1
                    q["issuerVariants"].add(str(holding.get("description") or ""))

        out = []
        for (ticker, security_id, signal), row in sorted(rows.items()):
            out.append({
                "ticker": ticker,
                "securityId": security_id,
                "signalDate": signal,
                "aggregateWeight": row["aggregateWeight"],
                "occurrenceCount": row["occurrenceCount"],
                "issuerVariants": sorted(x for x in row["issuerVariants"] if x),
            })
        module._H2_NPX_PIT_STATS = {
            "incrementalRecordCountInDecemberContainer": incremental_records,
            "visibleIssuerVariantOccurrencesBySignal": dict(sorted(visible_counts.items())),
            "blockedFutureIssuerVariantOccurrencesBySignal": dict(sorted(blocked_counts.items())),
            "unresolvedIdentityDateCount": len(out),
        }
        return out

    return unresolved


def configure(module, source_sha: str) -> None:
    h1 = load_module("h1_2007_country_wrapper", ROOT / "scripts/research-nq-series-id-pit-country-h1-2007.py")
    h1.configure(module, source_sha)
    module.MAPPING = MAPPING
    module.NPX = NPX
    module.BASE = BASE
    module.STRUCT = STRUCT
    module.SHARDS = SHARDS
    module.COUNTRY_OUT = COUNTRY_OUT
    module.GATE_OUT = DIAGNOSTIC_OUT
    module.unresolved = make_pit_unresolved(module)


def compute_pit_audit(module, mapping: dict, npx: dict, base: dict, struct: dict) -> dict:
    unresolved = module.unresolved(mapping, npx, base, struct)
    stats = dict(getattr(module, "_H2_NPX_PIT_STATS", {}))
    by_signal = defaultdict(lambda: {"identityDates": 0, "issuerVariants": 0})
    for row in unresolved:
        by_signal[row["signalDate"]]["identityDates"] += 1
        by_signal[row["signalDate"]]["issuerVariants"] += len(row.get("issuerVariants", []))
    return {
        **stats,
        "perSignalUnresolvedInput": {k: v for k, v in sorted(by_signal.items())},
        "rule": (
            "Pre-2007 frozen N-PX issuer variants are eligible throughout H2. A 2007 incremental N-PX issuer variant "
            "is visible only when sourceFilingDate <= signalDate and admittedAtSignal <= signalDate. Holding descriptions "
            "remain eligible. Future N-PX issuer variants are blocked; frozen country resolution/carry semantics are unchanged."
        ),
    }


def attach_lineage(path: Path, *, diagnostic: bool, pit_audit: dict) -> None:
    payload = json.loads(path.read_text())
    payload["purpose"] = (
        "H2 2007 period-extension country sensitivity diagnostic produced by the frozen strict PIT country semantics. "
        "SEC master-index coverage remains extended only through 2007, and incremental 2007 N-PX issuer variants are "
        "visible only when public by each signal date. This diagnostic is not a new gate and must not tune reconstruction or strategy performance."
        if diagnostic
        else
        "H2 2007 strict point-in-time country resolution for deterministic mapped COMMON_EQUITY holdings. The authoritative "
        "frozen H1 country implementation is reused; SEC master-index coverage remains through 2007, and the only H2-specific "
        "adaptation is signal-date filtering of incremental 2007 N-PX issuer-name variants. UNKNOWN remains UNKNOWN."
    )
    payload["validationDefinition"] = "docs/research/h2-2007-country-pit-issuer-variant-validation-definition.md"
    payload["sourceCatalogArtifactId"] = SOURCE_ARTIFACT_ID
    payload["sourceCatalogSha256"] = SOURCE_SHA
    payload["mappingRunId"] = MAPPING_RUN_ID
    payload["mappingArtifactId"] = MAPPING_ARTIFACT_ID
    payload["authoritativeH1CountryRunId"] = AUTHORITATIVE_H1_COUNTRY_RUN_ID
    payload["authoritativeH1CountryArtifactId"] = AUTHORITATIVE_H1_COUNTRY_ARTIFACT_ID
    payload["baseCountryEvidenceArtifactId"] = BASE_COUNTRY_ARTIFACT_ID
    payload["structuralCountryEvidenceArtifactId"] = STRUCTURAL_COUNTRY_ARTIFACT_ID
    payload["npxPitRunId"] = NPX_PIT_RUN_ID
    payload["npxPitArtifactId"] = NPX_PIT_ARTIFACT_ID
    payload["npxBaseArtifactId"] = NPX_BASE_ARTIFACT_ID
    payload["npxCountryContainerSignalMonth"] = "2007-12"
    payload["periodExtensionMasterYears"] = [2005, 2006, 2007]
    payload["npxIssuerVariantPitAudit"] = pit_audit
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("resolve-shard", "merge"), required=True)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=8)
    args = parser.parse_args()

    if int(os.environ.get("SOURCE_CATALOG_ARTIFACT_ID", "0")) != SOURCE_ARTIFACT_ID:
        raise RuntimeError("wrong fixed source artifact env")
    if os.environ.get("SOURCE_CATALOG_SHA256", "").strip().lower() != SOURCE_SHA:
        raise RuntimeError("wrong fixed source SHA env")
    if int(os.environ.get("MAPPING_RUN_ID", "0")) != MAPPING_RUN_ID or int(os.environ.get("MAPPING_ARTIFACT_ID", "0")) != MAPPING_ARTIFACT_ID:
        raise RuntimeError("wrong fixed mapping lineage env")

    mapping, npx = validate_upstream()
    module = load_module(
        "authoritative_h1_strict_pit_country",
        ROOT / "scripts/research-nq-hybrid-pit-country-gate-b-h1-2006.py",
    )
    configure(module, SOURCE_SHA)

    if args.mode == "resolve-shard":
        module.resolve_shard(args)
        return

    module.merge()
    base = json.loads(BASE.read_text())
    struct = json.loads(STRUCT.read_text())
    pit_audit = compute_pit_audit(module, mapping, npx, base, struct)
    attach_lineage(COUNTRY_OUT, diagnostic=False, pit_audit=pit_audit)
    attach_lineage(DIAGNOSTIC_OUT, diagnostic=True, pit_audit=pit_audit)

    country = json.loads(COUNTRY_OUT.read_text())
    print("H2_2007_COUNTRY_SUMMARY", json.dumps({
        "sourceCatalogSha256": country.get("catalogSha256"),
        "mappingArtifactId": MAPPING_ARTIFACT_ID,
        "npxPitArtifactId": NPX_PIT_ARTIFACT_ID,
        "reasonCounts": country.get("reasonCounts"),
        "npxIssuerVariantPitAudit": country.get("npxIssuerVariantPitAudit"),
        "monthly": [
            {
                "signalMonth": snap["signalMonth"],
                "sourceSeriesCount": snap["sourceSeriesCount"],
                "mappedCommonEquityCountryCounts": snap.get("mappedCommonEquityCountryCounts"),
                "mappedCommonEquityCountryWeights": snap.get("mappedCommonEquityCountryWeights"),
                "corpPositiveNonCorpNameCount": snap.get("corpPositiveNonCorpNameCount"),
            }
            for snap in country.get("monthSnapshots", [])
        ],
    }), flush=True)


if __name__ == "__main__":
    main()
