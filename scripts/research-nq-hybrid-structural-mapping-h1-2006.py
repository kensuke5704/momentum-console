#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "catalog_mapping",
    ROOT / "scripts/research-nq-catalog-structural-mapping-h1-2006.py",
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

module.RAW = ROOT / "data/research/nq-pit-holdings-hybrid-h1-2006.json"
module.OUT = ROOT / "data/research/nq-hybrid-structural-mapping-h1-2006.json"

if __name__ == "__main__":
    module.main()
