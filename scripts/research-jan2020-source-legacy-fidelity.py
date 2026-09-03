#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DISC=ROOT/'data/research/jan2020-source-legacy-nearest.json'
OUT=ROOT/'data/research/jan2020-source-legacy-fidelity.json'
SPEC=importlib.util.spec_from_file_location('nearest',ROOT/'scripts'/'research-transition-nearest-fidelity-2019.py')
nearest=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(nearest)

d=json.loads(DISC.read_text())
chosen={}
for sid,row in d.get('chosen',{}).items():
    chosen[sid]=(str(row['cik']),row['accession'],row['form'],row['reportDate'])
nearest.CHOSEN=chosen
nearest.OUT=OUT
nearest.main()
