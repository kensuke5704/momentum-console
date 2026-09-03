#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,re
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

# Production N-PORT bootstrap is already ASSET_CAT=EC / INVESTMENT_COUNTRY=US / ISSUER_TYPE=CORP.
# For this transition filing, EC is explicit COMMON STOCKS and country is explicitly printed.
# Therefore only rows between an explicit "United States - xx%" heading and "Total United States"
# are comparable to the Production-side country filter. No listing venue or missing-country inference is used.
def parse_name_first_us(seg):
    rows=[]; in_common=False; in_us=False; lines=seg.splitlines(); i=0
    while i<len(lines):
        raw=lines[i]; line=nearest.clean(raw)
        if re.search(r'\bCOMMON STOCKS?\b',line,re.I):
            in_common=True; in_us=False; i+=1; continue
        if in_common and re.match(r'^United States\s*[-–—]\s*\d',line,re.I):
            in_us=True; i+=1; continue
        if in_common and re.match(r'^Total United States\b',line,re.I):
            in_us=False; i+=1; continue
        if in_common and nearest.STOP_RE.search(line):
            in_common=False; in_us=False; i+=1; continue
        if not (in_common and in_us):
            i+=1; continue
        cells=[nearest.clean(c) for c in re.split(r'\t+',raw) if nearest.clean(c) not in {'','$','—','-'}]
        nums=[(k,nearest.num(c)) for k,c in enumerate(cells) if nearest.NUM_RE.match(c)]
        # Normal one-line form: issuer | shares | optional '$' | market value.
        if len(nums)>=2 and nums[0][0]>0:
            first_num=nums[0][0]; desc=' '.join(cells[:first_num]).strip(); value=nums[-1][1]
            if desc and value is not None and not desc.lower().startswith('total '):
                rows.append({'raw':desc,'name':nearest.norm(desc),'value':value,'country':'United States'})
            i+=1; continue
        # Occasional rendered split: issuer + shares on one line, value on the next.
        if len(nums)==1 and nums[0][0]>0 and i+1<len(lines):
            nxt=[nearest.clean(c) for c in re.split(r'\t+',lines[i+1]) if nearest.clean(c) not in {'','$','—','-'}]
            nxtnums=[nearest.num(c) for c in nxt if nearest.NUM_RE.match(c)]
            if nxtnums:
                desc=' '.join(cells[:nums[0][0]]).strip(); value=nxtnums[-1]
                if desc and value is not None and not desc.lower().startswith('total '):
                    rows.append({'raw':desc,'name':nearest.norm(desc),'value':value,'country':'United States'}); i+=2; continue
        i+=1
    return nearest.finish(rows)

# This Gate-B precursor intentionally uses the explicit-US grammar only. A zero-row series is reported
# as structurally unresolved rather than silently falling back to all-country holdings.
def parse_rows(seg):
    return ('name_first_explicit_us',parse_name_first_us(seg))
nearest.parse_rows=parse_rows
nearest.main()
