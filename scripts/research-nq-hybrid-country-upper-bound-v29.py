#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/research/nq-hybrid-country-resolved-h1-2006.json"
TMP = ROOT / "data/research/nq-hybrid-country-upper-bound-input-h1-2006.json"
OUT = ROOT / "data/research/nq-hybrid-universe-country-upper-bound-h1-2006.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    data = json.loads(SRC.read_text())
    changed = 0
    changed_weight = 0.0
    for snapshot in data["monthSnapshots"]:
        for filing in snapshot["sourceFilings"]:
            for holding in filing.get("holdings", []):
                if (
                    holding.get("mappingStatus") == "MATCHED_UNIQUE"
                    and holding.get("countryClassification") == "UNKNOWN"
                ):
                    holding["countryClassification"] = "US"
                    holding["countryReason"] = "COUNTRY_UPPER_BOUND_SENSITIVITY_ONLY"
                    changed += 1
                    changed_weight += float(holding.get("weight") or 0.0)

    data["purpose"] = (
        "Country upper-bound sensitivity only. Every already deterministically mapped holding whose historical "
        "country remains UNKNOWN is temporarily treated as US. Unmapped and ambiguous security identities remain "
        "excluded. This is never the primary Universe and is not used to select parser, mapping, eligibility or "
        "strategy rules."
    )
    data["countryUpperBoundChangedHoldingOccurrences"] = changed
    data["countryUpperBoundChangedWeightAcrossSnapshots"] = changed_weight
    TMP.write_text(json.dumps(data, indent=2) + "\n")

    universe = load("universe_upper", ROOT / "scripts/research-nq-hybrid-universe-h1-2006.py")
    universe.SRC = TMP
    universe.OUT = OUT
    universe.main()

    output = json.loads(OUT.read_text())
    output["sensitivityOnly"] = True
    output["countryUpperBoundChangedHoldingOccurrences"] = changed
    output["countryUpperBoundChangedWeightAcrossSnapshots"] = changed_weight
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print("COUNTRY_UPPER_BOUND", json.dumps({
        "changedHoldingOccurrences": changed,
        "changedWeightAcrossSnapshots": changed_weight,
        "months": len(output.get("monthSnapshots", [])),
    }), flush=True)


if __name__ == "__main__":
    main()
