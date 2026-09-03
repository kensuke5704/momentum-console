#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('d',ROOT/'scripts'/'research-transition-legacy-nearest-2019.py')
d=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(d)
# CIKs are registrant identities resolved independently from SEC series metadata.
d.TARGETS={
 '0001645194':['S000057700'],
 '0001479026':['S000063326'],
 '0001540305':['S000061208'],
}
d.OUT=ROOT/'data/research/production-jan2020-legacy-discovery.json'
d.main()
