#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HANDOFF = "docs/research/momentum-handoff-current.md"
EXEMPT = {
    HANDOFF,
    "scripts/check-handoff-freshness.py",
    ".github/workflows/research-handoff-freshness.yml",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def material(path: str) -> bool:
    if path in EXEMPT:
        return False
    if path.startswith("scripts/research-"):
        return True
    if path.startswith(".github/workflows/research-"):
        return True
    if path.startswith("docs/research/") and path.endswith(".md"):
        return True
    if path.startswith("data/research/"):
        return True
    return False


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-handoff-freshness.py BASE_SHA HEAD_SHA")
    base, head = sys.argv[1:]
    changed = [p for p in git("diff", "--name-only", base, head).splitlines() if p]
    material_changes = [p for p in changed if material(p)]

    if not material_changes:
        print("HANDOFF_FRESHNESS_PASS no material research changes")
        return

    if HANDOFF not in changed:
        print("Material research changes detected without canonical handoff update:")
        for path in material_changes:
            print(f"- {path}")
        raise SystemExit(f"update {HANDOFF} in the same change set")

    text = Path(HANDOFF).read_text(encoding="utf-8")
    m = re.search(r"^Last updated:\s*(\d{4}-\d{2}-\d{2})\s+JST\s*$", text, flags=re.M)
    if not m:
        raise SystemExit("canonical handoff must contain `Last updated: YYYY-MM-DD JST`")

    today_jst = datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    if m.group(1) != today_jst:
        raise SystemExit(
            f"canonical handoff date is {m.group(1)} but current JST date is {today_jst}; refresh it"
        )

    required_phrases = (
        "Current objective",
        "Current reproducibility status",
        "Historical-data preservation protocol",
        "Current active sequence",
        "Freshness protocol",
    )
    missing = [x for x in required_phrases if x not in text]
    if missing:
        raise SystemExit(f"canonical handoff is missing required current-state sections: {missing}")

    print("HANDOFF_FRESHNESS_PASS", {"materialChanges": len(material_changes), "dateJst": today_jst})


if __name__ == "__main__":
    main()
