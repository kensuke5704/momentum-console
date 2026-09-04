#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/research/nq-pit-holdings-catalog-h1-2006.json"
NPX = ROOT / "data/research/npx-security-master-2006.json"
OUT = ROOT / "data/research/nq-catalog-structural-mapping-h1-2006.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load_module("base_mapping", ROOT / "scripts/research-nq-npx-mapping-2006.py")
structural = load_module("structural_mapping", ROOT / "scripts/research-nq-npx-structural-mapping-2006.py")


def build_master(master: dict):
    by = defaultdict(set)
    rejected = 0
    for row in master["records"]:
        ticker, security_id = row.get("ticker"), row.get("securityId")
        if not base.valid_identity(ticker, security_id):
            if ticker or security_id:
                rejected += 1
            continue
        for key in base.edge_the_variants(base.norm(row["normalizedIssuer"])):
            by[key].add((ticker, security_id))
    return by, sorted(by), rejected


def map_holding(desc: str, by, names) -> dict:
    identities = []
    matched_alias = None
    method = None
    if base.artifact(desc):
        return {"mappingStatus": "PARSER_ARTIFACT"}

    for alias in base.aliases(desc):
        found = by.get(alias, set())
        if found:
            identities = sorted(found)
            matched_alias = alias
            method = "BASELINE_EXACT"
            break

    if not identities:
        adr_alias, adr_ids = base.unique_adr_base_alias(desc, by)
        if adr_ids:
            identities = adr_ids
            matched_alias = adr_alias
            method = "BASELINE_ADR_BASE_UNIQUE"

    if not identities:
        baseline_aliases = set(base.aliases(desc))
        for alias in structural.structural_aliases(desc):
            if alias in baseline_aliases:
                continue
            found = by.get(alias, set())
            if found:
                identities = sorted(found)
                matched_alias = alias
                method = "STRUCTURAL_SUFFIX_EXACT"
                break

    if not identities:
        candidates = set()
        for query in structural.structural_aliases(desc):
            if len(query) < 20:
                continue
            for name in names:
                if min(len(query), len(name)) >= 20 and (query.startswith(name) or name.startswith(query)):
                    candidates.update(by[name])
        if len(candidates) == 1:
            identities = sorted(candidates)
            aliases = structural.structural_aliases(desc)
            matched_alias = aliases[-1] if aliases else None
            method = "UNIQUE_LONG_PREFIX"

    out = {
        "mappingStatus": (
            "MATCHED_UNIQUE" if len(identities) == 1
            else "AMBIGUOUS" if len(identities) > 1
            else "UNMAPPED"
        )
    }
    if method:
        out["matchMethod"] = method
    if matched_alias:
        out["matchedAlias"] = matched_alias
    if identities:
        out["identities"] = [{"ticker": ticker, "securityId": security_id} for ticker, security_id in identities]
    if len(identities) == 1:
        out["mappedTicker"] = identities[0][0]
        out["mappedSecurityId"] = identities[0][1]
    return out


def main() -> None:
    raw = json.loads(RAW.read_text())
    master = json.loads(NPX.read_text())
    by, names, rejected_master = build_master(master)

    snapshots = []
    method_counts = Counter()
    for snap in raw["monthSnapshots"]:
        source_filings = []
        total_count = matched_count = ambiguous_count = unmapped_count = 0
        total_weight = matched_weight = ambiguous_weight = unmapped_weight = 0.0
        for filing in snap["sourceFilings"]:
            mapped_holdings = []
            for holding in filing.get("holdings", []):
                if holding.get("legacyAssetSection") != "COMMON_EQUITY":
                    continue
                weight = float(holding.get("weight") or 0.0)
                mapped = map_holding(holding["description"], by, names)
                row = {**holding, **mapped}
                mapped_holdings.append(row)
                if mapped.get("matchMethod"):
                    method_counts[mapped["matchMethod"]] += 1
                if mapped["mappingStatus"] == "PARSER_ARTIFACT":
                    continue
                total_count += 1
                total_weight += weight
                if mapped["mappingStatus"] == "MATCHED_UNIQUE":
                    matched_count += 1
                    matched_weight += weight
                elif mapped["mappingStatus"] == "AMBIGUOUS":
                    ambiguous_count += 1
                    ambiguous_weight += weight
                else:
                    unmapped_count += 1
                    unmapped_weight += weight
            source_filings.append({
                **{k: v for k, v in filing.items() if k != "holdings"},
                "commonEquityHoldingCount": len(mapped_holdings),
                "commonEquityWeight": sum(float(h.get("weight") or 0.0) for h in mapped_holdings),
                "mappedUniqueHoldingCount": sum(h["mappingStatus"] == "MATCHED_UNIQUE" for h in mapped_holdings),
                "mappedUniqueWeight": sum(float(h.get("weight") or 0.0) for h in mapped_holdings if h["mappingStatus"] == "MATCHED_UNIQUE"),
                "holdings": mapped_holdings,
            })
        snapshots.append({
            "signalMonth": snap["signalMonth"],
            "asOf": snap["asOf"],
            "sourceSeriesCount": len(source_filings),
            "commonEquityHoldingCount": total_count,
            "commonEquityWeight": total_weight,
            "uniqueMappedCount": matched_count,
            "uniqueMappedCountRate": matched_count / total_count if total_count else None,
            "uniqueMappedWeight": matched_weight,
            "uniqueMappedWeightRate": matched_weight / total_weight if total_weight else None,
            "ambiguousCount": ambiguous_count,
            "ambiguousWeight": ambiguous_weight,
            "unmappedCount": unmapped_count,
            "unmappedWeight": unmapped_weight,
            "sourceFilings": source_filings,
        })
        print("MONTH", json.dumps({
            "signalMonth": snap["signalMonth"],
            "sourceSeriesCount": len(source_filings),
            "commonEquityHoldingCount": total_count,
            "uniqueMappedCount": matched_count,
            "uniqueMappedCountRate": matched_count / total_count if total_count else None,
            "uniqueMappedWeightRate": matched_weight / total_weight if total_weight else None,
            "ambiguousCount": ambiguous_count,
            "unmappedCount": unmapped_count,
        }), flush=True)

    out = {
        "purpose": (
            "Catalog-driven H1 2006 deterministic security mapping after retaining only holdings explicitly "
            "attributed to COMMON_EQUITY sections. Mapping reuses the accepted frozen 2006 N-PX master and "
            "return-independent exact/ADR-unique/trailing-suffix/unique-long-prefix rules. Fuzzy/edit-distance "
            "candidates are never auto-accepted. No country defaulting, ranks, returns, or strategy outcomes are used."
        ),
        "npxMasterRule": master.get("sampleRule"),
        "npxPairedRecords": master.get("pairedRecords"),
        "rejectedMasterIdentities": rejected_master,
        "mappingRule": (
            "Baseline exact normalized issuer; ADR base only if unique; exact after accepted trailing "
            "footnote/share-class/jurisdiction cleanup; >=20-character prefix only when the union of candidate "
            "ticker/security identities is exactly one."
        ),
        "matchMethodCounts": dict(method_counts),
        "monthSnapshots": snapshots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "months": len(snapshots),
        "matchMethodCounts": out["matchMethodCounts"],
    }), flush=True)


if __name__ == "__main__":
    main()
