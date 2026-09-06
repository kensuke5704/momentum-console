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
base = load("schedule_bound_v29", ROOT / "scripts/research-nq-schedule-bound-parser-v29.py")

START_HEADINGS = (
    "SCHEDULE OF PORTFOLIO INVESTMENTS",
    "SCHEDULE OF INVESTMENTS",
    "PORTFOLIO OF INVESTMENTS",
    "PORTFOLIO HOLDINGS",
    "STATEMENT OF INVESTMENTS",
    "STATEMENT OF NET ASSETS",
    "SCHEDULE OF SECURITIES",
)
END_HEADING_RE = re.compile(
    r"^(?:STATEMENTS? OF OPERATIONS|STATEMENTS? OF CHANGES IN NET ASSETS|"
    r"STATEMENTS? OF ASSETS AND LIABILITIES|STATEMENTS? OF CASH FLOWS|"
    r"FINANCIAL HIGHLIGHTS|NOTES? TO FINANCIAL STATEMENTS)",
    re.I,
)
END_TOTAL_RE = re.compile(r"^(?:TOTAL INVESTMENTS?|NET ASSETS?)\b", re.I)
LEADING_QTY_RE = re.compile(
    r"^\s*(\d[\d,]*(?:\.\d+)?)\s+(.+?)\s+(?:([A-Z]{3})\s+)?\$?\s*(\(?\d[\d,]*(?:\.\d+)?\)?)\s*$",
    re.I,
)
NUM_ONLY_RE = re.compile(r"^\(?\$?\s*\d[\d,]*(?:\.\d+)?\s*\)?$")
SEPARATOR_RE = re.compile(r"^[-_= .]+$")
DATE_RE = re.compile(r"^(?:AS OF\s+)?(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\b.*\b20\d{2}\b", re.I)
PERCENT_HEADER_RE = re.compile(r"(?:--|[-–—]\s*)\(?\d+(?:\.\d+)?%\)?\s*$")
HEADER_RE = re.compile(
    r"^(?:COMMON STOCKS?|COMMON SHARES?|PREFERRED STOCKS?|PREFERRED SHARES?|SHORT[- ]TERM INVESTMENTS?|"
    r"MONEY MARKET(?: FUND)?|CORPORATE BONDS?|U\.S\. GOVERNMENT|TOTAL(?: INVESTMENTS?)?|NET ASSETS?|"
    r"SECURITY(?: DESCRIPTION)?|DESCRIPTION|SHARES?|NUMBER|OF SHARES|VALUE|MARKET VALUE|PRINCIPAL(?: AMOUNT)?|"
    r"PORTFOLIO SUMMARY|PORTFOLIO STATISTICS|FINANCIAL STATEMENTS|STATEMENT OF NET ASSETS|"
    r"SCHEDULE OF INVESTMENTS(?: \(CONTINUED\))?|PORTFOLIO OF INVESTMENTS(?: \(CONTINUED\))?)\b",
    re.I,
)
BAD_TEXT_RE = re.compile(
    r"\b(?:UNAUDITED|SEE NOTES? TO|NOTES? TO (?:THE )?(?:SCHEDULE|STATEMENT|PORTFOLIO)|"
    r"EXPENSES? ARE CALCULATED|AVERAGE ANNUAL TOTAL RETURNS?|FEDERAL INCOME TAXES|"
    r"FOREIGN CURRENCY TRANSLATION|TAX COST|UNREALIZED APPRECIATION|UNREALIZED DEPRECIATION|"
    r"CAPITAL SHARE TRANSACTIONS?|NET INCREASE|BEGINNING OF PERIOD|END OF PERIOD|RESPECTIVELY)\b",
    re.I,
)


def clean_desc(value: str) -> str:
    value = re.sub(r"\bTABLE OF CONTENTS\b", " ", value, flags=re.I)
    value = pilot.clean_desc(value)
    value = re.sub(r"\.{2,}", " ", value)
    return " ".join(value.split())


def is_start_heading(line: str) -> bool:
    up = " ".join(line.upper().split())
    return any(up.startswith(heading) for heading in START_HEADINGS)


def is_nonsecurity_text(line: str) -> bool:
    value = " ".join((line or "").split())
    if not value:
        return True
    if SEPARATOR_RE.fullmatch(value):
        return True
    if DATE_RE.search(value):
        return True
    if BAD_TEXT_RE.search(value):
        return True
    if PERCENT_HEADER_RE.search(value):
        return True
    if HEADER_RE.search(value):
        return True
    if value.upper().startswith(("ITEM ", "PAGE ")):
        return True
    return False


def security_text(value: str) -> bool:
    value = clean_desc(value)
    if len(value) < 3 or not re.search(r"[A-Za-z]{2}", value):
        return False
    if is_nonsecurity_text(value):
        return False
    return True


def emit(out: list[dict], description: str, quantity: float | None, market_value: float | None) -> None:
    description = clean_desc(description)
    if not security_text(description):
        return
    if market_value is None or market_value <= 0:
        return
    if quantity is not None and quantity <= 0:
        quantity = None
    out.append({
        "description": description,
        "quantityOrPrincipal": quantity,
        "marketValue": market_value,
    })


def parse_bound_plain_holdings(text: str) -> list[dict]:
    """Parse fixed-width/plain schedules already deterministically bound to one fund identity.

    Accepted grammars are structural only:
    - quantity + issuer + market value on one line;
    - issuer + quantity + market value on one line (including dot leaders);
    - issuer, quantity and market value on consecutive lines, with optional '$' line;
    - continuation issuer text followed by a numeric tail on the next line.

    Parsing starts only at an accepted complete-holdings heading and stops at total
    investments/net assets or the next non-holdings financial-statement heading. No
    ticker, future Series metadata, country inference, ranks, returns or strategy
    outcomes are used.
    """
    lines = pilot.plain_lines(text)
    holdings: list[dict] = []
    started = False
    pending_desc = ""
    pending_qty: float | None = None

    for raw in lines:
        line = " ".join(raw.split())
        if not line:
            continue
        up = line.upper()

        if is_start_heading(line):
            started = True
            pending_desc = ""
            pending_qty = None
            continue
        if not started:
            continue

        if END_HEADING_RE.search(line) or (END_TOTAL_RE.search(line) and len(holdings) >= 5):
            started = False
            pending_desc = ""
            pending_qty = None
            continue
        if up.startswith(("NOTES TO ", "NOTE TO ", "ITEM 2.", "ITEM 3.", "ITEM 4.")):
            started = False
            pending_desc = ""
            pending_qty = None
            continue
        if SEPARATOR_RE.fullmatch(line) or line in {"$", "—", "-"}:
            continue

        # Quantity-first fixed-width rows, common in PowerShares and First Trust.
        m = LEADING_QTY_RE.match(line)
        if m:
            qty_raw, desc_raw, _currency, value_raw = m.groups()
            qty = pilot.parse_number(qty_raw)
            value = pilot.parse_number(value_raw)
            if security_text(desc_raw) and qty is not None and qty > 0 and value is not None and value > 0:
                emit(holdings, desc_raw, qty, value)
                pending_desc = ""
                pending_qty = None
                continue

        # Issuer-first fixed-width rows, including dot-leader tables.
        m = pilot.TAIL_RE.match(line)
        if m:
            prefix, qty_raw, _currency, value_raw = m.groups()
            had_toc = bool(re.search(r"TABLE OF CONTENTS", prefix, re.I))
            desc = clean_desc(prefix)
            qty = pilot.parse_number(qty_raw)
            value = pilot.parse_number(value_raw)
            if qty is not None and qty > 0 and value is not None and value > 0:
                if had_toc and pending_desc:
                    desc = clean_desc(pending_desc + " " + desc)
                if security_text(desc):
                    emit(holdings, desc, qty, value)
                    pending_desc = ""
                    pending_qty = None
                    continue
                if pending_desc:
                    # A wrapped issuer can put only a footnote marker on the numeric tail line.
                    joined = clean_desc(" ".join(x for x in (pending_desc, desc) if x))
                    if security_text(joined):
                        emit(holdings, joined, qty, value)
                        pending_desc = ""
                        pending_qty = None
                        continue

        # Split-column fixed-width rows, common in iShares/Vanguard shareholder reports.
        if NUM_ONLY_RE.fullmatch(line):
            number = pilot.parse_number(line)
            if number is None or number <= 0 or not pending_desc:
                continue
            if pending_qty is None:
                pending_qty = number
            else:
                emit(holdings, pending_desc, pending_qty, number)
                pending_desc = ""
                pending_qty = None
            continue

        if is_nonsecurity_text(line):
            pending_desc = ""
            pending_qty = None
            continue

        desc = clean_desc(line)
        if security_text(desc):
            if pending_desc and pending_qty is None:
                pending_desc = clean_desc(pending_desc + " " + desc)
            else:
                pending_desc = desc
                pending_qty = None
        else:
            pending_desc = ""
            pending_qty = None

    return pilot.dedupe(holdings)


def parsed_holdings(combined: str) -> tuple[str, list[dict], float]:
    combined = corrected.trim_series_schedule(combined)
    bound_html = base.parse_bound_html_holdings(combined)
    bound_plain = parse_bound_plain_holdings(combined)

    if len(bound_plain) > len(bound_html):
        method = "schedule_bound_plain_v2"
        parsed = bound_plain
    else:
        method = "schedule_bound_html_v2"
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
