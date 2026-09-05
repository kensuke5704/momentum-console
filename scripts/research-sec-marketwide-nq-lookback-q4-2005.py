#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research/sec-marketwide-nq-lookback-q4-2005.json"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "application/zip,text/plain,*/*",
    "Accept-Encoding": "identity",
}
FORMS = {"N-Q", "N-Q/A"}
CUTOFF = "2005-12-31"


def fetch_master() -> tuple[str, str, int]:
    base = "https://www.sec.gov/Archives/edgar/full-index/2005/QTR4"
    zip_url = base + "/master.zip"
    req = urllib.request.Request(zip_url, headers=UA)
    with urllib.request.urlopen(req, timeout=50) as response:
        payload = response.read(25_000_000)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        member = next(name for name in archive.namelist() if name.lower().endswith("master.idx"))
        text = archive.read(member).decode("latin-1", "replace")
    return text, zip_url, len(payload)


def accession_from_filename(filename: str) -> str | None:
    match = re.search(r"edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$", filename, re.I)
    return match.group(2) if match else None


def index_url(cik: str, accession: str) -> str:
    compact = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{accession}-index.html"


def main() -> None:
    text, transport, zip_bytes = fetch_master()
    rows = []
    master_row_count = 0
    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) < 5 or not parts[0].strip().isdigit():
            continue
        master_row_count += 1
        cik, company, form, date_filed, filename = [part.strip() for part in parts[:5]]
        form = form.upper()
        if form not in FORMS or date_filed > CUTOFF:
            continue
        accession = accession_from_filename(filename)
        if not accession:
            continue
        rows.append({
            "cik": cik.zfill(10),
            "company": company,
            "form": form,
            "dateFiled": date_filed,
            "filename": filename,
            "accession": accession,
            "indexUrl": index_url(cik, accession),
            "quarter": "2005Q4",
        })

    rows.sort(key=lambda row: (row["dateFiled"], row["cik"], row["accession"], row["form"]))
    dedup = []
    seen = set()
    for row in rows:
        key = (row["accession"], row["form"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)
    rows = dedup

    out = {
        "purpose": (
            "Production-independent 2005 Q4 N-Q/N-Q-A lookback inventory for PIT Series/Class identity "
            "and, separately, for a later monthly selector to choose the latest N-Q public by a 2006 month end. "
            "Loading a filing into this lookback does not make its Series ETF-positive and does not make the "
            "filing a holdings source. Strict issuer-own operational evidence establishes ETF Series eligibility; "
            "the monthly catalog independently requires both evidenceDateFiled <= month end and N-Q dateFiled <= "
            "month end. No known source list, holdings outcomes, ranks, returns, or strategy results are used."
        ),
        "source": "SEC_MASTER_Q4_2005_NQ_LOOKBACK_V1",
        "cutoff": CUTOFF,
        "masterRowCount": master_row_count,
        "masterTransport": {"url": transport, "zipBytes": zip_bytes},
        "filingCount": len(rows),
        "uniqueRegistrantCiks": len({row["cik"] for row in rows}),
        "byForm": dict(Counter(row["form"] for row in rows)),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "source": out["source"],
        "filingCount": out["filingCount"],
        "uniqueRegistrantCiks": out["uniqueRegistrantCiks"],
        "byForm": out["byForm"],
    }), flush=True)


if __name__ == "__main__":
    main()
