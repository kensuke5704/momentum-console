#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


parser = load("schedule_bound_v29_v2", ROOT / "scripts/research-nq-schedule-bound-parser-v29-v2.py")
grouping = load("grouping_v29", ROOT / "scripts/research-nq-hybrid-grouping-v29.py")
hybrid = load("hybrid_holdings_final", ROOT / "scripts/research-nq-pit-holdings-hybrid-h1-2006.py")


def html_first_parsed_holdings(combined: str) -> tuple[str, list[dict], float]:
    """Preserve the already-validated HTML parser; fixed-width v2 is zero-only fallback."""
    trimmed = parser.corrected.trim_series_schedule(combined)
    html_rows = parser.base.parse_bound_html_holdings(trimmed)
    if not html_rows:
        return parser.parsed_holdings(combined)

    out=[]; seen=set()
    for holding in html_rows:
        desc=" ".join(str(holding.get("description") or "").split())
        value=max(0.0,float(holding.get("marketValue") or 0.0))
        quantity=holding.get("quantityOrPrincipal")
        if not desc or value<=0: continue
        key=(desc,quantity,value)
        if key in seen: continue
        seen.add(key)
        out.append({"description":desc,"marketValue":value,"quantityOrPrincipal":quantity})
    total=sum(row["marketValue"] for row in out)
    if total>0:
        for row in out: row["weight"]=100.0*row["marketValue"]/total
        out.sort(key=lambda row:row["weight"],reverse=True)
    return "schedule_bound_html_preserved",out,total


def annotate_sections_cached(holdings: list[dict], combined: str) -> tuple[list[dict], dict, dict]:
    vis=hybrid.seg.visible(combined); nv=hybrid.ec.ntext(vis); positions=[]
    for section,pattern in hybrid.ec.SECTION_PATTERNS:
        for match in pattern.finditer(nv): positions.append((match.start(),section))
    positions.sort(); counts=Counter(); weights=defaultdict(float); out=[]
    for holding in holdings:
        best_pos=None; best_alias=None
        for alias in hybrid.ec.holding_aliases(holding["description"]):
            start=0
            while True:
                pos=nv.find(alias,start)
                if pos<0: break
                if best_pos is None or pos<best_pos: best_pos=pos; best_alias=alias
                start=pos+max(1,len(alias))
        section="UNKNOWN"
        if best_pos is not None:
            prior=[(p,s) for p,s in positions if p<best_pos]
            if prior: section=max(prior,key=lambda item:item[0])[1]
        row={**holding,"legacyAssetSection":section}
        if best_alias: row["matchedSourceAlias"]=best_alias
        counts[section]+=1; weights[section]+=float(holding.get("weight") or 0); out.append(row)
    return out,dict(counts),dict(weights)


hybrid.corrected.parsed_holdings=html_first_parsed_holdings
hybrid.annotate_sections=annotate_sections_cached
hybrid.legacy_grouped_schedule_blocks=grouping.legacy_grouped_schedule_blocks
hybrid.seg.grouped_schedule_blocks=grouping.series_grouped_schedule_blocks

if __name__=="__main__":
    hybrid.main()
