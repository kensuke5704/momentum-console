#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = ROOT / "scripts/research-npx-pit-master-h2-2007.py"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "application/zip,text/plain,*/*",
    "Accept-Encoding": "identity",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load_module("h2_2007_npx_pit_base", BASE_SCRIPT)


def fetch_index_text_zip(requested_url: str) -> tuple[str, str]:
    if not requested_url.endswith("/master.idx"):
        raise RuntimeError(f"unexpected index URL: {requested_url}")
    zip_url = requested_url.removesuffix("/master.idx") + "/master.zip"
    req = urllib.request.Request(zip_url, headers=UA)
    with urllib.request.urlopen(req, timeout=50) as response:
        payload = response.read(25_000_000)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        member = next((name for name in archive.namelist() if name.lower().endswith("master.idx")), None)
        if not member:
            raise RuntimeError(f"master.idx missing from {zip_url}")
        text = archive.read(member).decode("latin-1", "replace")
    if not base.pilot.plausible_index(text):
        raise RuntimeError(f"unexpected SEC master.idx format extracted from {zip_url}")
    print(f"index {zip_url} zipBytes={len(payload):,}", flush=True)
    return text, zip_url


# Transport-only correction. All selection, parsing, normalization, PIT, and
# monthly-master semantics remain in the pre-defined base implementation.
base.pilot.fetch_index_text = fetch_index_text_zip

if __name__ == "__main__":
    base.main()
