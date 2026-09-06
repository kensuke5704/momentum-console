#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from bisect import bisect_left
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

BARE_MONTH_RE = re.compile(r"^(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)$", re.I)
REPORT_LABEL_RE = re.compile(
    r"(?:DATE OF REPORTING PERIOD|SIX MONTHS ENDED|SPECIAL MEETING OF SHAREHOLDERS|"
    r"SHAREHOLDER EXPENSES|ACCOUNT VALUE|EXPENSE RATIO|EXPENSES PAID|TABLE OF CONTENTS)",
    re.I,
)


def html_first_clean_v4(combined: str) -> tuple[str, list[dict], float]:
    trimmed = parser.corrected.trim_series_schedule(combined)
    html_rows = parser.base.parse_bound_html_holdings(trimmed)
    if html_rows:
        out = []
        seen = set()
        for holding in html_rows:
            desc = " ".join(str(holding.get("description") or "").split())
            value = max(0.0, float(holding.get("marketValue") or 0.0))
            quantity = holding.get("quantityOrPrincipal")
            if not desc or value <= 0:
                continue
            if parser.BAD_TEXT_RE.search(desc) or BARE_MONTH_RE.fullmatch(desc) or REPORT_LABEL_RE.search(desc):
                continue
            if parser.is_nonsecurity_text(desc):
                continue
            key = (desc, quantity, value)
            if key in seen:
                continue
            seen.add(key)
            out.append({"description": desc, "marketValue": value, "quantityOrPrincipal": quantity})
        out = parser.drop_page_split_suffix_duplicates(out)
        if out:
            total = sum(row["marketValue"] for row in out)
            for row in out:
                row["weight"] = 100.0 * row["marketValue"] / total
            out.sort(key=lambda row: row["weight"], reverse=True)
            return "schedule_bound_html_preserved_v4", out, total
    return parser.parsed_holdings(combined)


def annotate_sections_fast_exact(holdings: list[dict], combined: str) -> tuple[list[dict], dict, dict]:
    """Logic-equivalent section attribution with exact first-position and bisect caches."""
    vis = hybrid.seg.visible(combined)
    nv = hybrid.ec.ntext(vis)
    positions = []
    for section, pattern in hybrid.ec.SECTION_PATTERNS:
        for match in pattern.finditer(nv):
            positions.append((match.start(), section))
    positions.sort()
    section_positions = [p for p, _ in positions]
    section_names = [s for _, s in positions]

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
        if best_pos is not None and section_positions:
            idx = bisect_left(section_positions, best_pos) - 1
            if idx >= 0:
                section = section_names[idx]

        row = {**holding, "legacyAssetSection": section}
        if best_alias:
            row["matchedSourceAlias"] = best_alias
        counts[section] += 1
        weights[section] += float(holding.get("weight") or 0)
        out.append(row)

    return out, dict(counts), dict(weights)


hybrid.corrected.parsed_holdings = html_first_clean_v4
hybrid.annotate_sections = annotate_sections_fast_exact
hybrid.legacy_grouped_schedule_blocks = grouping.legacy_grouped_schedule_blocks
hybrid.seg.grouped_schedule_blocks = grouping.series_grouped_schedule_blocks

if __name__ == "__main__":
    hybrid.main()
