#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('nearest', ROOT/'scripts'/'research-transition-nearest-fidelity-2019.py')
nearest=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(nearest)

# Frozen from metadata-only expanded discovery run 33729506031.
# All pairs are exact seriesId continuity and <=184 days from the nearest pre-NPORT legacy report.
nearest.CHOSEN={
 'S000038223':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
 'S000047480':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
 'S000050191':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
 'S000051284':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
 'S000051348':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
 'S000053021':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
 'S000053022':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
 'S000058619':('1467831','0000894189-19-008202','N-CSR','2019-09-30'),
}
nearest.OUT=ROOT/'data'/'research'/'transition-shortgap-fidelity-2019.json'
nearest.main()
