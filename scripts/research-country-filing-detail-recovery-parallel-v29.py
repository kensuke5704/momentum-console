#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARD = int(os.environ.get("SHARD_INDEX", "0"))
SRC = ROOT / f"data/research/country-index-headers-recovery-v29-shard-{SHARD}.json"
OUT = ROOT / f"data/research/country-filing-detail-recovery-v29-shard-{SHARD}.json"

spec = importlib.util.spec_from_file_location(
    "filing_detail_base",
    ROOT / "scripts/research-country-filing-detail-recovery-v29.py",
)
base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(base)


def fetch_one(filename: str):
    try:
        text, transport = base.detail_page(filename)
        return filename, text, transport, None
    except Exception as exc:
        return filename, None, None, type(exc).__name__


def main() -> None:
    data = json.loads(SRC.read_text())
    rows = data.get("results") or []

    grouped = defaultdict(list)
    for row in rows:
        cik = str(row.get("historicalExactCik") or "").zfill(10)
        if cik.strip("0"):
            grouped[cik].append(row)

    union_by_cik = {}
    all_files = {}
    for cik, queries in grouped.items():
        union = {}
        for query in queries:
            for filing in base.candidates(query):
                union[filing["filename"]] = filing
                all_files[filing["filename"]] = filing
        union_by_cik[cik] = union

    fetched = {}
    errors = 0
    # Transport-only parallelism. Candidate selection and subsequent evidence
    # evaluation remain byte-for-byte equivalent in ordering/semantics to the
    # accepted serial recovery script.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_one, fn): fn for fn in sorted(all_files)}
        for done_i, future in enumerate(as_completed(futures), 1):
            fn, text, transport, error = future.result()
            if error:
                errors += 1
                fetched[fn] = (None, error)
            else:
                fetched[fn] = (text, transport)
            if done_i % 100 == 0:
                print(
                    "FETCH_PROGRESS",
                    json.dumps({"shard": SHARD, "done": done_i, "total": len(all_files), "errors": errors}),
                    flush=True,
                )

    pages_by_cik = {}
    for cik, union in union_by_cik.items():
        pages = {}
        for fn, filing in union.items():
            text, transport = fetched.get(fn, (None, "NOT_FETCHED"))
            pages[fn] = (filing, text, transport)
        pages_by_cik[cik] = pages

    results = []
    resolved = us = nonus = conflicts = 0
    for i, query in enumerate(rows, 1):
        cik = str(query.get("historicalExactCik") or "").zfill(10)
        targets = list(query.get("matchedIssuerForms") or query.get("issuerVariants") or [])
        rec = {
            "ticker": query.get("ticker"),
            "securityId": query.get("securityId"),
            "asOfReportDate": query.get("asOfReportDate"),
            "issuerVariants": query.get("issuerVariants", []),
            "matchedIssuerForms": targets,
            "historicalExactCik": cik if cik.strip("0") else None,
            "classification": "UNKNOWN",
            "attempts": [],
        }
        positives = []
        if cik.strip("0"):
            for filing in base.candidates(query):
                _filing, text, transport = pages_by_cik.get(cik, {}).get(
                    filing["filename"], (filing, None, "NOT_FETCHED")
                )
                one = {**filing}
                if text is None:
                    one["error"] = transport
                    rec["attempts"].append(one)
                    continue
                try:
                    state, name, role = base.detail_entity_state(targets, cik, text)
                    one.update(
                        {
                            "transport": transport,
                            "stateCode": state,
                            "historicalEntityName": name,
                            "entityRole": role,
                        }
                    )
                    if state:
                        positives.append(
                            {
                                "classification": "US" if state in base.US_CODES else "NON_US",
                                "stateCode": state,
                                "historicalEntityName": name,
                                "entityRole": role,
                                "evidenceForm": filing["form"],
                                "evidenceDateFiled": filing["dateFiled"],
                                "evidenceFilename": filing["filename"],
                                "evidenceTransport": transport,
                            }
                        )
                except Exception as exc:
                    one["error"] = type(exc).__name__
                rec["attempts"].append(one)

        classes = sorted({p["classification"] for p in positives})
        if len(classes) > 1:
            conflicts += 1
            raise RuntimeError(
                f"filing-detail country conflict {rec['ticker']} {rec['securityId']} "
                f"{rec['asOfReportDate']}: {classes}"
            )
        if len(classes) == 1:
            selected = next(p for p in positives if p["classification"] == classes[0])
            rec.update(selected)
            rec["resolutionSource"] = "PIT_FILING_DETAIL_ENTITY_STATE"
            resolved += 1
            us += rec["classification"] == "US"
            nonus += rec["classification"] == "NON_US"
        results.append(rec)
        if i % 50 == 0:
            print(
                "PROGRESS",
                json.dumps({"shard": SHARD, "done": i, "resolved": resolved, "errors": errors}),
                flush=True,
            )

    out = {
        "purpose": (
            "Semantics-identical transport-parallel execution of the accepted return-independent PIT filing-detail "
            "country recovery. Candidate selection and evidence evaluation are unchanged; only independent page "
            "fetches are concurrent. No current ticker metadata, current state/country, fuzzy matching, US default, "
            "ranks, returns or strategy outcomes are used."
        ),
        "shardIndex": SHARD,
        "shardCount": 8,
        "inputCount": len(rows),
        "historicalCikCount": len(grouped),
        "resolvedCount": resolved,
        "resolvedUSCount": us,
        "resolvedNonUSCount": nonus,
        "remainingUnknownCount": len(rows) - resolved,
        "transportErrorCount": errors,
        "detailCacheCount": len(all_files),
        "conflictCount": conflicts,
        "transportParallelism": 8,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
