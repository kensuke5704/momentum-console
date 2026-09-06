#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('strict_country_base',ROOT/'scripts/research-nq-hybrid-country-strict-v5-h1-2006.py')
strict=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(strict)
orig=strict.flat.base.submission_prefix
cache={}

def cached_submission_prefix(filename,max_bytes):
    key=(filename,int(max_bytes))
    if key not in cache:
        cache[key]=orig(filename,max_bytes)
    return cache[key]

strict.flat.base.submission_prefix=cached_submission_prefix
if __name__=='__main__':
    strict.main()
    print(f'STRICT_COUNTRY_EXACT_SUBMISSION_CACHE_SIZE {len(cache)}',flush=True)
