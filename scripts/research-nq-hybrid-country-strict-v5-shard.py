#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
MAPPING = R / "nq-hybrid-structural-mapping-h1-2006.json"
NPX = R / "npx-security-master-2006.json"
MASTER = R / "sec-issuer-master-rows-2005-2006.json"
OUTDIR = R / "country-shards"
RESOLVER_SCRIPT = os.environ.get(
    "STRICT_COUNTRY_SHARD_RESOLVER_SCRIPT",
    "research-nq-hybrid-country-strict-v5-seeded-evidence-cache.py",
)

spec = importlib.util.spec_from_file_location(
    "country_resolver",
    ROOT / "scripts" / RESOLVER_SCRIPT,
)
resolver = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(resolver)
strict = resolver.strict
resolve_one = (
    getattr(resolver, "pit_carry_resolve", None)
    or getattr(resolver, "seeded_resolve", None)
    or getattr(resolver, "cached_exact_historical_resolve", None)
)
if resolve_one is None:
    raise RuntimeError(f"resolver {RESOLVER_SCRIPT} exposes no supported exact historical resolver")


def collect_unresolved(mapping: dict, npx: dict) -> dict:
    issuers = strict.build_issuer_variants(npx)
    unresolved = {}
    for snapshot in mapping["monthSnapshots"]:
        for filing in snapshot["sourceFilings"]:
            report_date = filing.get("reportDate")
            for holding in filing.get("holdings", []):
                if holding.get("mappingStatus") != "MATCHED_UNIQUE":
                    continue
                explicit = holding.get("legacyCountryClassification")
                if explicit in {"US", "NON_US"}:
                    continue
                if strict.non_us_cins(holding.get("mappedSecurityId")):
                    continue
                if strict.RECEIPT.search(str(holding.get("description") or "")):
                    continue
                key = strict.identity_key(holding.get("mappedTicker"), holding.get("mappedSecurityId"))
                ukey = (key[0], key[1], report_date)
                unresolved.setdefault(ukey, {
                    "ticker": key[0],
                    "securityId": key[1],
                    "asOfReportDate": report_date,
                    "issuerVariants": sorted(issuers.get(key, set())),
                })
    return unresolved


def main() -> None:
    shard_index = int(os.environ["COUNTRY_SHARD_INDEX"])
    shard_count = int(os.environ["COUNTRY_SHARD_COUNT"])
    if not (0 <= shard_index < shard_count):
        raise SystemExit("invalid shard index/count")
    mapping = json.loads(MAPPING.read_text())
    npx = json.loads(NPX.read_text())
    master = json.loads(MASTER.read_text())
    master_rows = master["rows"]
    unresolved = collect_unresolved(mapping, npx)
    ordered = sorted(unresolved.items())
    selected = [(k, row) for pos, (k, row) in enumerate(ordered) if pos % shard_count == shard_index]
    results = []
    for _, row in selected:
        result = resolve_one(row, master_rows) if row.get("issuerVariants") and row.get("asOfReportDate") else {**row, "classification": "UNKNOWN", "attempts": []}
        results.append(result)
        print("STRICT_COUNTRY_SHARD", json.dumps({
            "shardIndex": shard_index,
            "ticker": result.get("ticker"),
            "securityId": result.get("securityId"),
            "asOfReportDate": result.get("asOfReportDate"),
            "classification": result.get("classification"),
            "acceptedEvidenceReuse": result.get("acceptedEvidenceReuse", False),
        }), flush=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = {
        "shardIndex": shard_index,
        "shardCount": shard_count,
        "resolverScript": RESOLVER_SCRIPT,
        "unresolvedTotalCount": len(unresolved),
        "selectedCount": len(selected),
        "resolutionAudit": results,
    }
    path = OUTDIR / f"country-resolution-shard-{shard_index:02d}.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print("COUNTRY_SHARD_SUMMARY", json.dumps({
        "shardIndex": shard_index,
        "selectedCount": len(selected),
        "resolvedUSCount": sum(x.get("classification") == "US" for x in results),
        "resolvedNonUSCount": sum(x.get("classification") == "NON_US" for x in results),
        "remainingUnknownCount": sum(x.get("classification") == "UNKNOWN" for x in results),
        "acceptedEvidenceReuseCount": sum(bool(x.get("acceptedEvidenceReuse")) for x in results),
        "resolverScript": RESOLVER_SCRIPT,
    }), flush=True)


if __name__ == "__main__":
    main()
