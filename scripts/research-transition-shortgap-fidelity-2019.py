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

# Structural grammar observed in the 2019 ETFMG N-CSR before fidelity results:
# issuer description, shares, optional '$' cell, market value. Country/industry headings
# contain no two numeric cells; totals contain no shares and are therefore excluded.
def parse_name_first(seg):
    rows=[]; in_common=False; lines=seg.splitlines(); i=0
    while i<len(lines):
        raw=lines[i]; line=nearest.clean(raw)
        if re.search(r'\bCOMMON STOCKS?\b',line,re.I):
            in_common=True; i+=1; continue
        if in_common and nearest.STOP_RE.search(line):
            in_common=False; i+=1; continue
        if not in_common:
            i+=1; continue
        cells=[nearest.clean(c) for c in re.split(r'\t+',raw) if nearest.clean(c) not in {'','$','—','-'}]
        nums=[(k,nearest.num(c)) for k,c in enumerate(cells) if nearest.NUM_RE.match(c)]
        # Normal one-line form: name | shares | value.
        if len(nums)>=2 and nums[0][0]>0:
            first_num=nums[0][0]; desc=' '.join(cells[:first_num]).strip(); value=nums[-1][1]
            if desc and value is not None and not desc.lower().startswith('total '):
                rows.append({'raw':desc,'name':nearest.norm(desc),'value':value})
            i+=1; continue
        # Occasional rendered split: name + shares on one line, value on next line.
        if len(nums)==1 and nums[0][0]>0 and i+1<len(lines):
            nxt=[nearest.clean(c) for c in re.split(r'\t+',lines[i+1]) if nearest.clean(c) not in {'','$','—','-'}]
            nxtnums=[nearest.num(c) for c in nxt if nearest.NUM_RE.match(c)]
            if nxtnums:
                desc=' '.join(cells[:nums[0][0]]).strip(); value=nxtnums[-1]
                if desc and value is not None and not desc.lower().startswith('total '):
                    rows.append({'raw':desc,'name':nearest.norm(desc),'value':value}); i+=2; continue
        i+=1
    return nearest.finish(rows)

_old_parse_rows=nearest.parse_rows
def parse_rows(seg):
    candidates=[('name_first',parse_name_first(seg)),_old_parse_rows(seg)]
    plausible=[x for x in candidates if 5<=len(x[1])<=250]
    if plausible:return max(plausible,key=lambda x:len(x[1]))
    return max(candidates,key=lambda x:len(x[1]))
nearest.parse_rows=parse_rows
nearest.main()
