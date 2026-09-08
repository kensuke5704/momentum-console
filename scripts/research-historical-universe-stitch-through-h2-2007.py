#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"
PREFIX = DATA / "historical-universe-builder-through-h1-2007.json"
H2 = DATA / "historical-universe-builder-h2-2007.json"
H2_VALIDATION = DATA / "h2-2007-downstream-period-extension-validation.json"
OUT = DATA / "historical-universe-builder-through-h2-2007.json"

BUILDER_BLOB = "1357402f34dfea1c1dbdcaac7de5078b680eb5c3"
PREFIX_ARTIFACT_ID = 10040792563
H2_ARTIFACT_ID = 10042811090
H2_RUN_ID = 34192853738
H2_SOURCE_SHA = "9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631"


def main() -> None:
    prefix = json.loads(PREFIX.read_text())
    h2 = json.loads(H2.read_text())
    validation = json.loads(H2_VALIDATION.read_text())

    assert prefix.get("builderGitBlob") == BUILDER_BLOB
    assert validation.get("passed") is True
    assert validation.get("sourceCatalogSha256") == H2_SOURCE_SHA
    assert validation.get("checks", {}).get("frozenBuilderExactParitySixOfSix") is True
    assert validation.get("checks", {}).get("countryNoLookahead") is True
    assert validation.get("checks", {}).get("corpBridgeMaterialityInvariant") is True
    assert h2.get("catalogSha256") == H2_SOURCE_SHA

    prefix_months = prefix.get("monthSnapshots", [])
    h2_months = h2.get("monthSnapshots", [])
    expected_prefix = [f"2006-{m:02d}" for m in range(1, 13)] + [f"2007-{m:02d}" for m in range(1, 7)]
    expected_h2 = [f"2007-{m:02d}" for m in range(7, 13)]
    assert [row.get("signalMonth") for row in prefix_months] == expected_prefix
    assert [row.get("signalMonth") for row in h2_months] == expected_h2

    for key in ("eligibilityOrder", "sourceEligibility", "breadthRule"):
        assert prefix.get(key) == h2.get(key), (key, prefix.get(key), h2.get(key))

    combined = prefix_months + h2_months
    expected = expected_prefix + expected_h2
    assert [row.get("signalMonth") for row in combined] == expected
    assert len(combined) == 24
    assert len({row.get("signalMonth") for row in combined}) == 24
    assert all(str(row.get("asOf") or "").startswith(row["signalMonth"]) for row in combined)
    assert all(len(row.get("symbols", [])) <= 80 for row in combined)

    output = {
        "purpose": (
            "Frozen validated historical-Universe stitch through H2 2007. It preserves the closed 18-month "
            "2006-01 through 2007-06 prefix exactly and appends only the independently downstream-validated "
            "H2 2007 frozen-builder output, without recomputing historical reconstruction or strategy performance."
        ),
        "definition": "docs/research/h2-2007-24-month-stitch-validation-definition.md",
        "builderGitBlob": BUILDER_BLOB,
        "segments": [
            {
                "period": "2006-01..2007-06",
                "runId": 34186850426,
                "artifactId": PREFIX_ARTIFACT_ID,
                "validation": "closed validated 18-month prefix",
            },
            {
                "period": "2007-07..2007-12",
                "runId": H2_RUN_ID,
                "artifactId": H2_ARTIFACT_ID,
                "sourceCatalogSha256": H2_SOURCE_SHA,
                "validation": "H2 2007 downstream frozen-builder exact parity",
            },
        ],
        "eligibilityOrder": prefix.get("eligibilityOrder"),
        "sourceEligibility": prefix.get("sourceEligibility"),
        "breadthRule": prefix.get("breadthRule"),
        "monthSnapshots": combined,
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")

    reread = json.loads(OUT.read_text())
    rows = reread["monthSnapshots"]
    assert rows[:18] == prefix_months
    assert rows[18:] == h2_months
    print("STITCH_THROUGH_H2_2007", json.dumps({
        "passed": True,
        "months": len(rows),
        "first": rows[0]["signalMonth"],
        "last": rows[-1]["signalMonth"],
        "eligibleSourceSeriesCounts": [row.get("eligibleSourceSeriesCount") for row in rows],
        "universeSizes": [len(row.get("symbols", [])) for row in rows],
    }, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
