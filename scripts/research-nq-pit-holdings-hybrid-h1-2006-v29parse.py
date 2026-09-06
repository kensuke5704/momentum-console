#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


bound = load("schedule_bound_v29", ROOT / "scripts/research-nq-schedule-bound-parser-v29.py")
hybrid = load("hybrid_holdings", ROOT / "scripts/research-nq-pit-holdings-hybrid-h1-2006.py")

# The original extractor already receives blocks deterministically segmented to a
# legacy title or explicit Series ID. Replace parsing only; source selection,
# schedule assignment and identity logic remain frozen.
hybrid.corrected.parsed_holdings = bound.parsed_holdings

if __name__ == "__main__":
    hybrid.main()
