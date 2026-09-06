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


final_v3 = load("final_v3_base", ROOT / "scripts/research-nq-pit-holdings-hybrid-h1-2006-v29final-v3.py")
hybrid = final_v3.hybrid
parser = final_v3.parser
grouping = load("grouping_v29_v3_for_holdings", ROOT / "scripts/research-nq-hybrid-grouping-v29-v3.py")


def annotate_sections_fast_exact(holdings: list[dict], combined: str) -> tuple[list[dict], dict, dict]:
    """Logic-equivalent asset-section attribution with first-position caching.

    The prior implementation enumerated every occurrence of every issuer alias even
    though only the earliest occurrence was retained. str.find(alias) returns that
    same earliest position. Caching by exact alias changes computation only, not
    matching semantics, section rules, source text, or eligibility.
    """
    vis = hybrid.seg.visible(combined)
    nv = hybrid.ec.ntext(vis)
    positions = []
    for section, pattern in hybrid.ec.SECTION_PATTERNS:
        for match in pattern.finditer(nv):
            positions.append((match.start(), section))
    positions.sort()

    alias_first_pos: dict[str, int] = {}
    counts = Counter()
    weights = defaultdict(float)
    out = []

    for holding in holdings:
        best_pos = None
        best_alias = None
        for alias in hybrid.ec.holding_aliases(holding["description"]):
            if alias not in alias_first_pos:
                alias_first_pos[alias] = nv.find(alias)
            pos = alias_first_pos[alias]
            if pos >= 0 and (best_pos is None or pos < best_pos):
                best_pos = pos
                best_alias = alias

        section = "UNKNOWN"
        if best_pos is not None:
            # positions are sorted; retain the same nearest-prior-section rule.
            prior_section = None
            for p, s in positions:
                if p >= best_pos:
                    break
                prior_section = s
            if prior_section is not None:
                section = prior_section

        row = {**holding, "legacyAssetSection": section}
        if best_alias:
            row["matchedSourceAlias"] = best_alias
        counts[section] += 1
        weights[section] += float(holding.get("weight") or 0)
        out.append(row)

    return out, dict(counts), dict(weights)


hybrid.annotate_sections = annotate_sections_fast_exact
hybrid.legacy_grouped_schedule_blocks = grouping.legacy_grouped_schedule_blocks
hybrid.seg.grouped_schedule_blocks = grouping.series_grouped_schedule_blocks

if __name__ == "__main__":
    hybrid.main()
