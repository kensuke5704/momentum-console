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
OUT = ROOT / "data" / "research" / "sec-complete-portfolio-inventory-h1-2006.json"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "application/zip,text/plain,*/*",
    "Accept-Encoding": "identity",
}
ACCEPTED_FORMS = {"N-Q", "N-Q/A", "N-CSR", "N-CSR/A", "N-CSRS", "N-CSRS/A"}
FORM_PREFIX = re.compile(r"^N-(?:Q|CSR)", re.I)


def fetch(url: str, limit: int = 30_000_000, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit)


def load_master(year: int, quarter: int) -> tuple[str, str]:
    base = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}"
    zip_url = base + "/master.zip"
    try:
        payload = fetch(zip_url)
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith("master.idx"))
            return zf.read(name).decode("latin-1", "replace"), zip_url
    except Exception:
        idx_url = base + "/master.idx"
        return fetch(idx_url).decode("latin-1", "replace"), idx_url


def accession_from_filename(filename: str) -> str | None:
    m = re.search(r"/(\d{10}-\d{2}-\d{6})\.txt$", filename, re.I)
    return m.group(1) if m else None


def index_url(filename: str) -> str | None:
    m = re.search(r"edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$", filename, re.I)
    if not m:
        return None
    cik_dir = str(int(m.group(1)))
    accession = m.group(2)
    return f"https://www.sec.gov/Archives/edgar/data/{cik_dir}/{accession.replace('-', '')}/{accession}-index.html"


def parse_master(text: str, quarter: int) -> tuple[list[dict], Counter]:
    rows: list[dict] = []
    candidate_forms: Counter = Counter()
    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) < 5 or not parts[0].strip().isdigit():
            continue
        cik, company, form, date_filed, filename = [x.strip() for x in parts[:5]]
        form = form.upper()
        if FORM_PREFIX.search(form):
            candidate_forms[form] += 1
        if form not in ACCEPTED_FORMS:
            continue
        accession = accession_from_filename(filename)
        rows.append({
            "cik": cik.zfill(10), "company": company, "form": form, "dateFiled": date_filed,
            "filename": filename, "accession": accession, "indexUrl": index_url(filename), "quarter": quarter,
        })
    return rows, candidate_forms


def main() -> None:
    all_rows: list[dict] = []
    transports: dict[str, str] = {}
    observed: Counter = Counter()
    for quarter in (1, 2):
        text, transport = load_master(2006, quarter)
        rows, forms = parse_master(text, quarter)
        all_rows.extend(rows); observed.update(forms); transports[f"2006Q{quarter}"] = transport
        print("QUARTER", json.dumps({"quarter": quarter, "acceptedRows": len(rows), "candidateForms": dict(sorted(forms.items())), "transport": transport}), flush=True)
    all_rows.sort(key=lambda r: (r["dateFiled"], r["form"], r["cik"], r["filename"]))
    accessions = {r["accession"] for r in all_rows if r["accession"]}; ciks = {r["cik"] for r in all_rows}
    form_counts = Counter(r["form"] for r in all_rows)
    out = {
        "purpose": "Production-independent 2006 H1 complete-portfolio filing inventory from official SEC quarterly master indexes. Includes N-Q/N-Q-A and certified annual/semiannual shareholder-report forms N-CSR/N-CSRS plus amendments. No known ETF source accessions, holdings outcomes, ranks, returns, or strategy results are used.",
        "year": 2006, "quarters": [1, 2], "acceptedForms": sorted(ACCEPTED_FORMS),
        "observedCandidateForms": dict(sorted(observed.items())), "transport": transports,
        "filingCount": len(all_rows), "uniqueAccessionCount": len(accessions),
        "duplicateAccessionCount": len(all_rows) - len(accessions), "uniqueRegistrantCikCount": len(ciks),
        "formCounts": dict(sorted(form_counts.items())), "firstFiledDate": all_rows[0]["dateFiled"] if all_rows else None,
        "lastFiledDate": all_rows[-1]["dateFiled"] if all_rows else None, "rows": all_rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k:v for k,v in out.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
