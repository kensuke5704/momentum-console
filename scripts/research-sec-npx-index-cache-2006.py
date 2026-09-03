#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research/sec-npx-index-2006.json"
UA = {
    "User-Agent": "momentum-console research kensuke5704@users.noreply.github.com",
    "Accept": "application/zip,application/octet-stream,*/*",
}
BASE = "https://www.sec.gov/Archives/edgar/full-index/2006/QTR{q}/master.zip"
TARGET_FORMS = {"N-PX", "N-PX/A"}


def fetch_zip(url: str, attempts: int = 4) -> bytes:
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if len(data) < 100_000 or not data.startswith(b"PK"):
                raise ValueError(f"unexpected master.zip response bytes={len(data):,}")
            print(f"fetched {url} bytes={len(data):,} attempt={attempt}", flush=True)
            return data
        except Exception as e:
            last = e
            print(f"attempt {attempt}/{attempts} failed {url}: {e!r}", flush=True)
            if attempt < attempts:
                time.sleep(2 * attempt)
    raise RuntimeError(f"unable to fetch {url}") from last


def parse_master_zip(data: bytes, q: int) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        name = next((n for n in names if n.lower().endswith("master.idx")), None)
        if not name:
            raise ValueError(f"QTR{q}: master.idx missing in ZIP: {names[:10]}")
        text = z.read(name).decode("latin-1", "replace")
    rows = []
    for line in text.splitlines():
        p = line.split("|")
        if len(p) < 5:
            continue
        cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
        form = form.upper()
        if form not in TARGET_FORMS or not date_filed.startswith("2006"):
            continue
        rows.append({
            "cik": cik,
            "company": company,
            "form": form,
            "dateFiled": date_filed,
            "filename": filename,
            "quarter": q,
        })
    return rows


def main() -> None:
    rows = []
    sources = []
    for q in range(1, 5):
        url = BASE.format(q=q)
        data = fetch_zip(url)
        qr = parse_master_zip(data, q)
        print(f"QTR{q} N-PX rows={len(qr)}", flush=True)
        rows.extend(qr)
        sources.append({"quarter": q, "url": url, "bytes": len(data), "rows": len(qr)})
    uniq = {(r["cik"], r["form"], r["dateFiled"], r["filename"]): r for r in rows}
    rows = sorted(uniq.values(), key=lambda r: (r["dateFiled"], int(r["cik"] or 0), r["filename"]))
    primary = [r for r in rows if r["form"] == "N-PX"]
    out = {
        "year": 2006,
        "purpose": "Frozen official SEC EDGAR N-PX filing index for structural historical security mapping. No return/performance data used.",
        "source": "Official SEC EDGAR quarterly full-index master.zip",
        "sources": sources,
        "rowCount": len(rows),
        "primaryNpxCount": len(primary),
        "uniqueCikCount": len({r["cik"] for r in primary}),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
