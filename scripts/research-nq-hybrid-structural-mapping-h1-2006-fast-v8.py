#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mapping_base_v8',ROOT/'scripts/research-nq-hybrid-structural-mapping-h1-2006.py')
wrapper=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(wrapper)
module=wrapper.module
orig=module.map_holding
cache={}

def cached_map_holding(desc,by,names):
    # map_holding is a pure function of exact description + the single frozen
    # master indexes built once by main(). Reuse only exact-description results;
    # no normalization/fuzzy expansion is introduced here.
    if desc not in cache:
        cache[desc]=orig(desc,by,names)
    return dict(cache[desc])

module.map_holding=cached_map_holding
module.RAW=ROOT/'data/research/nq-pit-holdings-hybrid-h1-2006.json'
module.OUT=ROOT/'data/research/nq-hybrid-structural-mapping-h1-2006.json'

if __name__=='__main__':
    module.main()
    print(f'MAPPING_EXACT_DESCRIPTION_CACHE_SIZE {len(cache)}',flush=True)
