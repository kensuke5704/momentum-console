#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pilot = load("nqpilot", ROOT / "scripts/research-nq-parser-pilot.py")
corrected = load("corrected_base", ROOT / "scripts/research-nq-pit-holdings-2006-corrected.py")

CATEGORY = re.compile(
    r"(?:\bTOTAL\b|\bNET ASSETS?\b|\bTOTAL INVESTMENTS?\b|\bCOMMON STOCKS?\b\s*[-–—(]|"
    r"\bPREFERRED STOCKS?\b\s*[-–—(]|\bSHORT[- ]TERM\b\s*[-–—(]|\bMONEY MARKET\b\s*[-–—(]|"
    r"\bCORPORATE BONDS?\b\s*[-–—(]|\bU\.S\. GOVERNMENT\b\s*[-–—(]|\bSECURITY\b\s*$|"
    r"\bSHARES?\b\s*$|\bVALUE\b\s*$)",
    re.I,
)


def security_text(value: str) -> bool:
    value = " ".join((value or "").split())
    if len(value) < 3 or not re.search(r"[A-Za-z]{2}", value):
        return False
    if CATEGORY.search(value):
        return False
    return True


def parse_bound_html_holdings(text: str) -> list[dict]:
    """Parse HTML rows from a block already deterministically bound to one Series schedule.

    The generic pilot parser waits for a schedule heading inside a table row. Historical
    filings commonly place that heading outside the holdings table, even though the
    caller has already segmented the exact schedule block. This parser therefore starts
    at the first row, but accepts only security-like rows with a positive final numeric
    market-value cell and at least one other positive numeric cell (normally shares or
    principal). It does not use ticker, country, future metadata, ranks, returns or
    strategy outcomes.
    """
    holdings = []
    for cells in pilot.html_rows(text):
        values = []
        for index, cell in enumerate(cells):
            if not pilot.is_value_cell(cell):
                continue
            value = pilot.parse_number(cell)
            if value is not None and value > 0:
                values.append((index, value))
        if len(values) < 2:
            continue

        value_index, market_value = values[-1]
        text_cells = [
            (index, " ".join(cell.split()))
            for index, cell in pilot.text_candidates(cells)
            if index < value_index and security_text(cell)
        ]
        if not text_cells:
            continue

        # Security description is text, not holdings-content similarity. Longest cell
        # is robust to blank spacer columns in 2006 PowerShares/iShares/Vanguard tables.
        desc_index, description = max(text_cells, key=lambda item: (len(item[1]), -item[0]))
        if not security_text(description):
            continue

        other_numbers = [(index, value) for index, value in values[:-1] if value > 0]
        quantity = other_numbers[0][1] if len(other_numbers) == 1 else None
        holdings.append({
            "description": description,
            "quantityOrPrincipal": quantity,
            "marketValue": market_value,
        })

    return pilot.dedupe(holdings)


def parsed_holdings(combined: str) -> tuple[str, list[dict], float]:
    combined = corrected.trim_series_schedule(combined)

    bound_html = parse_bound_html_holdings(combined)
    _, plain = pilot.parse_plain_holdings(combined)

    # Yield choice is format detection only, matching the existing pilot convention.
    # No market returns or strategy results are consulted.
    if len(plain) > len(bound_html):
        method = "schedule_bound_plain"
        parsed = plain
    else:
        method = "schedule_bound_html"
        parsed = bound_html

    out = []
    seen = set()
    for holding in parsed:
        desc = " ".join(str(holding.get("description") or "").split())
        value = max(0.0, float(holding.get("marketValue") or 0.0))
        quantity = holding.get("quantityOrPrincipal")
        if not desc or value <= 0:
            continue
        key = (desc, quantity, value)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "description": desc,
            "marketValue": value,
            "quantityOrPrincipal": quantity,
        })

    total = sum(row["marketValue"] for row in out)
    if total > 0:
        for row in out:
            row["weight"] = 100.0 * row["marketValue"] / total
        out.sort(key=lambda row: row["weight"], reverse=True)
    return method, out, total
