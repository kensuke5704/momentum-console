#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "strict_country_indexed_base",
    ROOT / "scripts/research-nq-hybrid-country-strict-v5-indexed-cache.py",
)
indexed = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(indexed)
strict = indexed.strict
base_resolve = indexed.indexed_exact_historical_resolve

# exact_historical_resolve depends on reportDate + issuerVariants for its evidence query.
# ticker/securityId are carried only as output identity metadata and are not used to discover
# the historical CIK or state. Cache only the evidence portion for an exact query key.
_resolution_cache: dict[tuple[tuple[str, ...], str | None], dict] = {}
_INPUT_KEYS = {"ticker", "securityId", "asOfReportDate", "issuerVariants"}


def cached_exact_historical_resolve(row: dict, master_rows: list[dict]) -> dict:
    key = (tuple(str(x) for x in row.get("issuerVariants", [])), row.get("asOfReportDate"))
    if key not in _resolution_cache:
        resolved = base_resolve(row, master_rows)
        _resolution_cache[key] = {k: v for k, v in resolved.items() if k not in _INPUT_KEYS}
    return {**row, **_resolution_cache[key]}


strict.exact_historical_resolve = cached_exact_historical_resolve

if __name__ == "__main__":
    strict.main()
    print(
        "STRICT_COUNTRY_RESOLUTION_CACHE_SUMMARY",
        json.dumps({
            "resolutionCacheSize": len(_resolution_cache),
            "submissionCacheSize": len(indexed._submission_cache),
            "masterIndexedCompanyCount": len(indexed._master_by_normalized_company),
        }),
        flush=True,
    )
