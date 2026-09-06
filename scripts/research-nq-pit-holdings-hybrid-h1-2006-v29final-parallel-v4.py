#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path(os.environ.get("CATALOG_PATH", str(ROOT / "data/research/sec-hybrid-etf-source-catalog-h1-2006.json")))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


final = load("final_v4_parallel", ROOT / "scripts/research-nq-pit-holdings-hybrid-h1-2006-v29final-v4.py")
hybrid = final.hybrid
original_fetch = hybrid.fetch_submission


def prefetch():
    catalog = json.loads(CATALOG.read_text())
    filenames = sorted({s["filename"] for snap in catalog["monthSnapshots"] for s in snap["sourceFilings"]})
    cache = {}
    errors = {}
    print("PREFETCH_START", json.dumps({"uniqueFilingCount": len(filenames), "maxWorkers": 4}), flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(original_fetch, filename): filename for filename in filenames}
        for future in as_completed(futures):
            filename = futures[future]
            try:
                cache[filename] = future.result()
                print("PREFETCH_OK", filename, flush=True)
            except Exception as exc:
                errors[filename] = f"{type(exc).__name__}: {str(exc)[:500]}"
                print("PREFETCH_ERROR", filename, errors[filename], flush=True)
    if errors:
        raise RuntimeError(f"authoritative prefetch failures: {json.dumps(errors)}")
    print("PREFETCH_DONE", json.dumps({"successCount": len(cache), "errorCount": 0}), flush=True)
    return cache


def main():
    cache = prefetch()
    hybrid.fetch_submission = lambda filename: cache[filename]
    hybrid.main()


if __name__ == "__main__":
    main()
