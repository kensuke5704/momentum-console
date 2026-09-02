#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "research" / "beancounter-fund-holdings-2006.json"
BASE = "https://huggingface.co/datasets/bradfordlevy/BeanCounter/resolve/main/train"
TARGET_SHARDS = range(143, 166)  # include boundary shards; rows are filtered to calendar 2006
TARGET_FORMS = {"N-Q", "N-Q/A", "N-CSR", "N-CSR/A", "N-CSRS", "N-CSRS/A"}
UA = {
    "User-Agent": "momentum-console research kensuke5704@users.noreply.github.com",
    "Accept": "application/gzip",
}

# Conservative CUSIP-like token. Standard CUSIPs are 9 chars and normally end in a check digit.
# Requiring at least one letter avoids many dates/account numbers. Validation/mapping is a later stage.
CUSIP_RE = re.compile(r"(?<![A-Z0-9])([0-9A-Z]{8}[0-9])(?![A-Z0-9])")


def cusips_from_text(text: str) -> set[str]:
    up = text.upper()
    out: set[str] = set()
    for m in CUSIP_RE.finditer(up):
        token = m.group(1)
        if any(c.isalpha() for c in token):
            out.add(token)
    return out


def shard_url(idx: int) -> str:
    return f"{BASE}/bc-{idx:03d}-of-512.jsonl.gz"


def main() -> None:
    by_accession: dict[str, dict] = {}
    attachment_counts = Counter()
    shard_summaries = []
    malformed = 0

    for shard in TARGET_SHARDS:
        url = shard_url(shard)
        req = urllib.request.Request(url, headers=UA)
        rows = target_rows = target_attachments = 0
        min_date = None
        max_date = None
        print(f"SHARD {shard} start", flush=True)
        with urllib.request.urlopen(req, timeout=600) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for raw in gz:
                    rows += 1
                    try:
                        obj = json.loads(raw)
                    except Exception:
                        malformed += 1
                        continue
                    date = str(obj.get("date") or "")
                    if date:
                        min_date = date if min_date is None else min(min_date, date)
                        max_date = date if max_date is None else max(max_date, date)
                    if not date.startswith("2006-"):
                        continue
                    target_rows += 1
                    form = str(obj.get("type_filing") or "")
                    if form not in TARGET_FORMS:
                        continue
                    target_attachments += 1
                    accession = str(obj.get("accession") or "")
                    if not accession:
                        continue
                    attachment_counts[form] += 1
                    rec = by_accession.setdefault(
                        accession,
                        {
                            "accession": accession,
                            "date": date,
                            "form": form,
                            "attachments": 0,
                            "cusips": set(),
                            "filenames": [],
                        },
                    )
                    rec["date"] = min(rec["date"], date)
                    rec["attachments"] += 1
                    filename = obj.get("filename")
                    if filename and len(rec["filenames"]) < 8:
                        rec["filenames"].append(filename)
                    text = str(obj.get("text") or "")
                    rec["cusips"].update(cusips_from_text(text))
        shard_summaries.append(
            {
                "shard": shard,
                "rows": rows,
                "targetYearRows": target_rows,
                "targetFundAttachments": target_attachments,
                "minDate": min_date,
                "maxDate": max_date,
            }
        )
        print(
            f"SHARD {shard} done rows={rows:,} targetYear={target_rows:,} "
            f"fundAttachments={target_attachments:,} range={min_date}..{max_date}",
            flush=True,
        )

    filings = []
    filing_freq = Counter()
    form_counts = Counter()
    with_cusip = 0
    for accession, rec in sorted(by_accession.items(), key=lambda kv: (kv[1]["date"], kv[0])):
        cs = sorted(rec["cusips"])
        if cs:
            with_cusip += 1
            filing_freq.update(cs)
        form_counts[rec["form"]] += 1
        filings.append(
            {
                "accession": accession,
                "date": rec["date"],
                "form": rec["form"],
                "attachments": rec["attachments"],
                "cusipCount": len(cs),
                "cusips": cs,
                "sampleFilenames": rec["filenames"],
            }
        )

    ranked = [
        {"cusip": cusip, "filingFrequency": count}
        for cusip, count in filing_freq.most_common(500)
    ]
    summary = {
        "year": 2006,
        "source": "bradfordlevy/BeanCounter train shards",
        "targetShards": list(TARGET_SHARDS),
        "targetForms": sorted(TARGET_FORMS),
        "uniqueFilings": len(filings),
        "formCounts": dict(form_counts),
        "attachmentCounts": dict(attachment_counts),
        "filingsWithCusipLike": with_cusip,
        "filingCusipCoverage": with_cusip / len(filings) if filings else None,
        "uniqueCusipLike": len(filing_freq),
        "malformedRows": malformed,
        "shards": shard_summaries,
        "topCusips": ranked,
        "filings": filings,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "SUMMARY",
        json.dumps(
            {k: v for k, v in summary.items() if k not in {"filings", "topCusips", "shards"}},
            sort_keys=True,
        ),
        flush=True,
    )
    print("TOP_CUSIPS", json.dumps(ranked[:50]), flush=True)


if __name__ == "__main__":
    main()
