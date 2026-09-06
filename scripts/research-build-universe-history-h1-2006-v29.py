#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
GATE = R / "momentum-v2-9-final-gate-b-v10-h1-2006.json"
UNIVERSE = R / "nq-hybrid-universe-h1-2006.json"
COUNTRY = R / "nq-hybrid-country-resolved-h1-2006.json"
OUT = R / "universe-history-h1-2006-v29.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


universe_rules = load_module(
    "historical_universe_rules",
    ROOT / "scripts/research-nq-hybrid-universe-h1-2006.py",
)


def filing_accession(row: dict) -> str:
    value = row.get("accession") or row.get("sourceAccession")
    if not value:
        raise RuntimeError(
            "Eligible historical source filing is missing accession; do not invent Production-compatible provenance: "
            + json.dumps({k: row.get(k) for k in ("canonicalIdentity", "seriesId", "seriesName", "sourceFilename", "filingDate")})
        )
    return str(value)


def filing_series_id(row: dict) -> str:
    # Pre-ID rows legitimately have no SEC Series ID. Preserve their frozen canonical
    # contemporaneous identity in the schema field rather than backfilling a future ID.
    value = row.get("seriesId") or row.get("canonicalIdentity") or row.get("legacyIdentity")
    if not value:
        raise RuntimeError("Historical source is missing both Series ID and canonical contemporaneous identity")
    return str(value)


def main() -> None:
    gate = json.loads(GATE.read_text())
    if gate.get("gateBPass") is not True or gate.get("universeReconstructionConfirmed") is not True:
        raise SystemExit("Gate B is not PASS; historical builder is intentionally blocked")
    if gate.get("stage21PerformanceConsulted") is not False or gate.get("productionModified") is not False:
        raise SystemExit("Gate B provenance invariant failed")

    universe = json.loads(UNIVERSE.read_text())
    country = json.loads(COUNTRY.read_text())
    country_by_month = {x["signalMonth"]: x for x in country["monthSnapshots"]}

    history = []
    previous_symbols: set[str] = set()
    for snap in universe["monthSnapshots"]:
        month = snap["signalMonth"]
        csnap = country_by_month[month]
        eligible = [f for f in csnap["sourceFilings"] if universe_rules.source_eligibility(f)[0]]
        source_filings = sorted(
            [
                {
                    "accession": filing_accession(f),
                    "seriesId": filing_series_id(f),
                    "seriesName": str(f.get("seriesName") or ""),
                    "filingDate": str(f.get("filingDate") or ""),
                }
                for f in eligible
            ],
            key=lambda x: (x["seriesId"], x["filingDate"], x["accession"]),
        )
        if len(source_filings) != int(snap["eligibleSourceSeriesCount"]):
            raise RuntimeError(
                f"eligible source count mismatch {month}: builder={len(source_filings)} universe={snap['eligibleSourceSeriesCount']}"
            )

        symbols = [
            {
                "symbol": str(x["symbol"]),
                "universeRank": int(x["universeRank"]),
                "etfCount": int(x["etfCount"]),
                "aggregateWeight": float(x["aggregateWeight"]),
                "maxWeight": float(x["maxWeight"]),
                "recencyWeight": float(x["recencyWeight"]),
                "universeScore": float(x["universeScore"]),
            }
            for x in snap["symbols"]
        ]
        current_symbols = {x["symbol"] for x in symbols}
        history.append(
            {
                "signalMonth": month,
                "asOf": snap["asOf"],
                "symbols": symbols,
                "sourceFilings": source_filings,
                "added": sorted(current_symbols - previous_symbols),
                "removed": sorted(previous_symbols - current_symbols),
            }
        )
        previous_symbols = current_symbols

    output = {
        "purpose": "Research-only Production-compatible UniverseMonth history smoke test after corrected Gate B PASS. No Production data file is written and no Stage21 performance is executed.",
        "gateDecisionFile": str(GATE.relative_to(ROOT)),
        "inputUniverseFile": str(UNIVERSE.relative_to(ROOT)),
        "inputCountryFile": str(COUNTRY.relative_to(ROOT)),
        "productionSchema": "UniverseMonth: signalMonth/asOf/symbols/sourceFilings/added/removed",
        "productionModified": False,
        "stage21PerformanceExecuted": False,
        "history": history,
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        "HISTORICAL_BUILDER_H1_2006",
        json.dumps(
            {
                "monthCount": len(history),
                "months": [x["signalMonth"] for x in history],
                "universeSizes": [len(x["symbols"]) for x in history],
                "eligibleSourceCounts": [len(x["sourceFilings"]) for x in history],
                "output": str(OUT.relative_to(ROOT)),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
