#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Phase:
    name: str
    start: date
    end: date
    gate_env: str | None


PHASES = (
    Phase("DEVELOPMENT", date(2006, 1, 1), date(2010, 12, 31), None),
    Phase("VALIDATION", date(2011, 1, 1), date(2014, 12, 31), "ALLOW_LEGACY_VALIDATION_PERFORMANCE"),
    Phase("SEALED_HOLDOUT", date(2015, 1, 1), date(2018, 12, 31), "ALLOW_LEGACY_SEALED_HOLDOUT_PERFORMANCE"),
)


def parse_date(raw: str) -> date:
    return date.fromisoformat(raw)


def gate_is_open(phase: Phase) -> bool:
    if phase.name == "DEVELOPMENT":
        return True
    if phase.name == "VALIDATION":
        return os.environ.get("ALLOW_LEGACY_VALIDATION_PERFORMANCE") == "1"
    if phase.name == "SEALED_HOLDOUT":
        return (
            os.environ.get("ALLOW_LEGACY_VALIDATION_PERFORMANCE") == "1"
            and os.environ.get("ALLOW_LEGACY_SEALED_HOLDOUT_PERFORMANCE") == "1"
        )
    return False


def assert_performance_window(start: date, end: date) -> list[str]:
    if end < start:
        raise SystemExit("end date precedes start date")
    if start < PHASES[0].start or end > PHASES[-1].end:
        raise SystemExit("legacy performance guard only permits dates inside 2006-01-01..2018-12-31")

    touched: list[str] = []
    for phase in PHASES:
        overlaps = start <= phase.end and end >= phase.start
        if not overlaps:
            continue
        touched.append(phase.name)
        if not gate_is_open(phase):
            if phase.name == "SEALED_HOLDOUT":
                requirement = "ALLOW_LEGACY_VALIDATION_PERFORMANCE=1 and ALLOW_LEGACY_SEALED_HOLDOUT_PERFORMANCE=1"
            else:
                requirement = f"{phase.gate_env}=1"
            raise SystemExit(
                f"performance window touches sealed phase {phase.name} "
                f"({phase.start}..{phase.end}); requires {requirement} only after prior evaluation gates are formally completed"
            )
    return touched


def main() -> None:
    ap = argparse.ArgumentParser(description="Enforce staged opening of 2006-2018 legacy performance history.")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()
    touched = assert_performance_window(parse_date(args.start), parse_date(args.end))
    print("PERFORMANCE_WINDOW_ALLOWED", {"start": args.start, "end": args.end, "phases": touched})


if __name__ == "__main__":
    main()
