#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

ORIGINAL = repro.ov.master_2020
# Bootstrap-first structural sample: First Trust has many 2020 N-PORT series
# with quarterly reports. No performance/rank information is used here.
TARGET = re.compile(r'FIRST TRUST', re.I)


def filtered_master():
    return [x for x in ORIGINAL() if TARGET.search(str(x.get('company') or ''))]


repro.ov.master_2020 = filtered_master
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'
repro.main()
