#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


hybrid = load("hybrid_base", ROOT / "scripts/research-nq-pit-holdings-hybrid-h1-2006.py")
seg = hybrid.seg
h2diag = hybrid.h2diag
legacy = hybrid.legacy


def marker_is_notes_reference(text: str, marker: re.Match) -> bool:
    """Reject 'Notes to [the] Schedule/Statement ...' references as portfolio boundaries."""
    prefix = text[max(0, marker.start() - 120):marker.start()]
    visible_prefix = h2diag.line_text(prefix).upper()
    tail = visible_prefix[-100:]
    return bool(re.search(r"(?:SEE\s+)?NOTES?\s+TO(?:\s+THE)?\s*$", tail))


def valid_markers(text: str, pattern: re.Pattern) -> list[re.Match]:
    return [m for m in pattern.finditer(text) if not marker_is_notes_reference(text, m)]


def series_grouped_schedule_blocks(primary_text: str, series: list[dict]) -> tuple[dict[str, list[str]], list[dict]]:
    markers = valid_markers(primary_text, h2diag.SCHEDULE)
    grouped: dict[str, list[str]] = {}
    audit: list[dict] = []
    for idx, marker in enumerate(markers):
        start = marker.start()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else min(len(primary_text), start + 300000)
        block = primary_text[start:end]
        assigned, rule = seg.assign_marker_series(primary_text, marker, series)
        audit.append({
            "markerIndex": idx,
            "marker": seg.visible(marker.group(0)),
            "assignmentRule": rule,
            "seriesId": assigned.get("seriesId") if assigned else None,
            "seriesName": assigned.get("seriesName") if assigned else None,
        })
        if assigned and assigned.get("seriesId"):
            grouped.setdefault(assigned["seriesId"], []).append(block)
    return grouped, audit


def legacy_grouped_schedule_blocks(primary_text: str, targets: dict[str, dict]) -> tuple[dict[str, list[str]], list[dict]]:
    visible = h2diag.line_text(primary_text)
    markers = valid_markers(visible, h2diag.SCHEDULE)
    target_by_norm = {row["normalizedSeriesName"]: iid for iid, row in targets.items()}
    grouped: dict[str, list[str]] = defaultdict(list)
    audit: list[dict] = []
    carry: str | None = None

    for idx, marker in enumerate(markers):
        next_start = markers[idx + 1].start() if idx + 1 < len(markers) else len(visible)
        before = visible[max(0, marker.start() - 1800):marker.start()].splitlines()[-18:]
        after = visible[marker.end():min(len(visible), marker.end() + 1800)].splitlines()[:18]
        window = {
            "markerIndex": idx,
            "marker": marker.group(0),
            "beforeLines": before,
            "afterLines": after,
        }
        candidates = legacy.title_candidates(window)
        exact = sorted({target_by_norm[c["normalizedTitle"]] for c in candidates if c["normalizedTitle"] in target_by_norm})
        meaningful_titles = sorted({c["normalizedTitle"] for c in candidates})

        rule = "UNASSIGNED"
        assigned: str | None = None
        if len(exact) == 1:
            carry = exact[0]
            assigned = carry
            rule = "EXACT_NORMALIZED_TITLE_AT_MARKER"
        elif len(exact) > 1:
            carry = None
            rule = "AMBIGUOUS_EXACT_TARGETS"
        elif meaningful_titles:
            carry = None
            rule = "DIFFERENT_MEANINGFUL_TITLE_BOUNDARY"
        elif carry:
            assigned = carry
            rule = "UNTITLED_CONTINUATION_OF_EXACT_TARGET"

        if assigned:
            start = max(0, marker.start() - 1600) if rule == "EXACT_NORMALIZED_TITLE_AT_MARKER" else marker.start()
            grouped[assigned].append(visible[start:next_start])

        audit.append({
            "markerIndex": idx,
            "marker": marker.group(0),
            "candidateTitles": meaningful_titles,
            "exactTargetIdentities": exact,
            "assignedIdentity": assigned,
            "assignmentRule": rule,
        })

    return dict(grouped), audit
