#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repro', ROOT / 'scripts' / 'research-legacy-universe-reproducibility-2020.py')
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

ORIGINAL = repro.ov.master_2020
TARGET = re.compile(r'FIRST TRUST', re.I)


def robust_download(path: Path) -> None:
    last = None
    for attempt in range(4):
        try:
            url = repro.ov.DRIVE + f'&attempt={attempt}'
            req = urllib.request.Request(url, headers=repro.ov.UA)
            with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
                while True:
                    b = r.read(1024 * 1024)
                    if not b:
                        break
                    f.write(b)
            if path.stat().st_size > 1_000_000 and zipfile.is_zipfile(path):
                return
            last = RuntimeError(f'invalid archive bytes={path.stat().st_size}')
        except Exception as e:
            last = e
        time.sleep(3 * (attempt + 1))
    raise last or RuntimeError('master archive download failed')


repro.ov.download = robust_download


def filtered_master():
    return [x for x in ORIGINAL() if TARGET.search(str(x.get('company') or ''))]


repro.ov.master_2020 = filtered_master
repro.OUT = ROOT / 'data' / 'research' / 'legacy-universe-reproducibility-fast-2020.json'
repro.main()
