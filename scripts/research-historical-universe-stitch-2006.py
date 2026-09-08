#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"

H1 = DATA / "historical-universe-builder-h1-2006.json"
H2 = DATA / "historical-universe-builder-h2-2006.json"
OUT = DATA / "historical-universe-builder-2006.json"

H1_ARTIFACT_ID = 10020226749
H2_ARTIFACT_ID = 10039694610
H1_CATALOG_SHA = "e2405277fe03a4208e163a43d724fd7364e139ad229caa70251b151f1d53b801"
H2_CATALOG_SHA = "f79f8d9e6d7fe45cb115a9c7f087dcca00622ff602cc0147e70e860f3528417d"
BUILDER_BLOB = "1357402f34dfea1c1dbdcaac7de5078b680eb5c3"

EXPECTED_MONTHS = [f"2006-{month:02d}" for month in range(1, 13)]


def main() -> None:
    h1 = json.loads(H1.read_text())
    h2 = json.loads(H2.read_text())

    assert h1.get("catalogSha256") == H1_CATALOG_SHA
    assert h2.get("catalogSha256") == H2_CATALOG_SHA

    for key in ("eligibilityOrder", "sourceEligibility", "breadthRule"):
        assert h1.get(key) == h2.get(key), (key, h1.get(key), h2.get(key))

    h1_months = h1.get("monthSnapshots", [])
    h2_months = h2.get("monthSnapshots", [])
    assert [row.get("signalMonth") for row in h1_months] == EXPECTED_MONTHS[:6]
    assert [row.get("signalMonth") for row in h2_months] == EXPECTED_MONTHS[6:]

    combined = h1_months + h2_months
    assert [row.get("signalMonth") for row in combined] == EXPECTED_MONTHS
    assert len({row.get("signalMonth") for row in combined}) == 12
    assert all(str(row.get("asOf") or "").startswith(row["signalMonth"]) for row in combined)
    assert all(len(row.get("symbols", [])) <= 80 for row in combined)

    output = {
        "purpose": (
            "Frozen 2006 full-year historical Universe stitch. It concatenates the separately exact-parity-validated "
            "H1 and H2 outputs from the same frozen historical-Universe builder without recomputing, reranking, "
            "repairing identities, resolving country, or reading Stage21 strategy outcomes."
        ),
        "builderGitBlob": BUILDER_BLOB,
        "segments": [
            {
                "period": "2006-H1",
                "artifactId": H1_ARTIFACT_ID,
                "catalogSha256": H1_CATALOG_SHA,
                "validation": "historical-universe-builder H1 exact parity 6/6",
            },
            {
                "period": "2006-H2",
                "artifactId": H2_ARTIFACT_ID,
                "catalogSha256": H2_CATALOG_SHA,
                "validation": "H2 downstream period-extension exact parity 6/6",
            },
        ],
        "eligibilityOrder": h1.get("eligibilityOrder"),
        "sourceEligibility": h1.get("sourceEligibility"),
        "breadthRule": h1.get("breadthRule"),
        "monthSnapshots": combined,
    }

    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        "FULL_YEAR_2006_STITCH",
        json.dumps(
            {
                "months": len(combined),
                "first": combined[0]["signalMonth"],
                "last": combined[-1]["signalMonth"],
                "eligibleSourceSeriesCounts": [row.get("eligibleSourceSeriesCount") for row in combined],
                "universeSizes": [len(row.get("symbols", [])) for row in combined],
            },
            separators=(",", ":"),
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
