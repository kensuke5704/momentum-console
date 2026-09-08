#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/research/npx-security-master-2006.json"
OUT_DIR = ROOT / "data/research"
AUDIT = OUT_DIR / "npx-pit-master-h2-2007-audit.json"
SAMPLE_COUNT = 64
SIGNALS = [
    ("2007-07", "2007-07-31"),
    ("2007-08", "2007-08-31"),
    ("2007-09", "2007-09-28"),
    ("2007-10", "2007-10-31"),
    ("2007-11", "2007-11-30"),
    ("2007-12", "2007-12-31"),
]
BROAD_CIKS = {
    "35348",      # Fidelity
    "826473",     # Vanguard
    "68138",      # Vanguard
    "745463",     # Eaton Vance
    "752737",     # Oppenheimer
    "81247",      # Putnam
    "916403",     # ING
    "814232",     # RS Investments
    "1039949",    # UBS
    "202385",     # Salomon Brothers
    "1026708",    # Wilshire
}
INDEX_BASE = "https://www.sec.gov/Archives/edgar/full-index/2007/QTR{q}/master.idx"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pilot = load_module("frozen_npx_parser", ROOT / "scripts/research-npx-security-master-2006.py")
builder = load_module("frozen_npx_builder", ROOT / "scripts/research-npx-security-master-build-2006.py")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def filing_index_2007() -> list[dict]:
    hits = []
    index_sources = []
    for q in range(1, 5):
        text, transport = pilot.fetch_index_text(INDEX_BASE.format(q=q))
        index_sources.append({"quarter": q, "transport": transport})
        for line in text.splitlines():
            parts = line.split("|")
            if len(parts) < 5:
                continue
            cik, company, form, date_filed, filename = [x.strip() for x in parts[:5]]
            form = form.upper()
            if form not in {"N-PX", "N-PX/A"} or not date_filed.startswith("2007"):
                continue
            hits.append({
                "cik": cik,
                "company": company,
                "form": form,
                "dateFiled": date_filed,
                "filename": filename,
            })
    unique = {(x["cik"], x["form"], x["dateFiled"], x["filename"]): x for x in hits}
    rows = sorted(unique.values(), key=lambda x: (x["dateFiled"], int(x["cik"]), x["filename"]))
    return rows, index_sources


def representatives(public_primary: list[dict]) -> list[dict]:
    by_cik: dict[str, dict] = {}
    for row in sorted(public_primary, key=lambda x: (x["dateFiled"], int(x["cik"]), x["filename"])):
        by_cik.setdefault(row["cik"], row)
    return sorted(by_cik.values(), key=lambda x: (int(x["cik"]), x["dateFiled"], x["filename"]))


def deterministic_quantile_sample(reps: list[dict], n: int = SAMPLE_COUNT) -> list[dict]:
    if len(reps) <= n:
        return list(reps)
    positions = [round(i * (len(reps) - 1) / (n - 1)) for i in range(n)]
    return [reps[p] for p in positions]


def source_key(row: dict) -> tuple[str, str, str, str]:
    return (row["cik"], row["form"], row["dateFiled"], row["filename"])


def record_key(row: dict) -> tuple[str, str | None, str | None]:
    return (row.get("normalizedIssuer") or "", row.get("ticker"), row.get("securityId"))


def main() -> None:
    if not BASE.exists():
        raise FileNotFoundError(f"missing frozen N-PX base: {BASE}")
    base = json.loads(BASE.read_text())
    base_records = list(base.get("records", []))
    base_keys = [record_key(r) for r in base_records]
    if len(base_keys) != len(set(base_keys)):
        raise RuntimeError("frozen base contains duplicate identity keys; refusing to mutate/deduplicate it")

    filings, index_sources = filing_index_2007()
    primary = [x for x in filings if x["form"] == "N-PX"]
    amendments = [x for x in filings if x["form"] == "N-PX/A"]
    print("INDEX", json.dumps({
        "totalNpxInventory": len(filings),
        "primaryNpx": len(primary),
        "amendments": len(amendments),
        "months": dict(Counter(x["dateFiled"][:7] for x in filings)),
    }), flush=True)

    admitted: dict[tuple[str, str, str, str], dict] = {}
    month_selection: dict[str, dict] = {}
    for signal_month, as_of in SIGNALS:
        public_primary = [x for x in primary if x["dateFiled"] <= as_of]
        reps = representatives(public_primary)
        sampled = deterministic_quantile_sample(reps)
        broad = [x for x in reps if x["cik"] in BROAD_CIKS]
        selected = {source_key(x): x for x in sampled + broad}
        new_keys = []
        for key, row in sorted(selected.items(), key=lambda kv: (kv[1]["dateFiled"], int(kv[1]["cik"]), kv[1]["filename"])):
            if key not in admitted:
                admitted[key] = {**row, "admittedAtSignal": as_of}
                new_keys.append(key)
        month_selection[signal_month] = {
            "signalMonth": signal_month,
            "asOf": as_of,
            "publicPrimaryFilings": len(public_primary),
            "publicRepresentativeCiks": len(reps),
            "quantileSelectedSources": len(sampled),
            "broadSelectedSources": len(broad),
            "selectedUniqueSources": len(selected),
            "newAdmissions": len(new_keys),
            "cumulativeAdmissions": len(admitted),
            "selectedSources": [selected[k] for k in sorted(selected)],
        }
        print("SELECTION", json.dumps({k: v for k, v in month_selection[signal_month].items() if k != "selectedSources"}), flush=True)

    parsed_by_source: dict[tuple[str, str, str, str], list[dict]] = {}
    source_results = []
    fetch_errors = []
    admitted_rows = sorted(admitted.values(), key=lambda x: (x["dateFiled"], int(x["cik"]), x["filename"]))
    for i, source in enumerate(admitted_rows, 1):
        key = source_key(source)
        try:
            text = pilot.fetch_text(pilot.sec_url(source["filename"]))
            parsed = pilot.parse_records(text)
            rows = []
            for rec in parsed:
                rows.append({
                    "issuer": rec["issuer"],
                    "normalizedIssuer": builder.normalize_issuer(rec["issuer"]),
                    "ticker": rec.get("ticker"),
                    "securityId": rec.get("securityId"),
                    "meetingDateRaw": rec.get("meetingDateRaw"),
                    "sourceFilingDate": source["dateFiled"],
                    "sourceCik": source["cik"],
                    "sourceCompany": source["company"],
                    "sourceFilename": source["filename"],
                    "admittedAtSignal": source["admittedAtSignal"],
                    "sourceForm": source["form"],
                })
            parsed_by_source[key] = rows
            paired = sum(bool(r.get("ticker") and r.get("securityId")) for r in rows)
            source_results.append({**source, "fetchOk": True, "records": len(rows), "pairedRecords": paired})
            print(f"SOURCE {i}/{len(admitted_rows)} {source['dateFiled']} CIK={source['cik']} records={len(rows)} paired={paired}", flush=True)
        except Exception as exc:
            fetch_errors.append({**source, "error": repr(exc)})
            source_results.append({**source, "fetchOk": False, "error": repr(exc)})
            print(f"SOURCE {i}/{len(admitted_rows)} FAIL {source['dateFiled']} CIK={source['cik']} {exc!r}", flush=True)
        if i < len(admitted_rows):
            time.sleep(0.20)

    if fetch_errors:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT.write_text(json.dumps({
            "status": "FAIL",
            "reason": "admitted N-PX source fetch/parse error",
            "baseArtifactId": 9876020712,
            "baseSha256": sha256_file(BASE),
            "fetchErrors": fetch_errors,
            "sourceResults": source_results,
        }, indent=2) + "\n")
        raise RuntimeError(f"{len(fetch_errors)} admitted N-PX source fetch/parse failures")

    monthly = []
    previous_incremental_source_keys: set[tuple[str, str, str, str]] = set()
    violations = []
    for signal_month, as_of in SIGNALS:
        active_sources = {
            key: row for key, row in admitted.items()
            if row["admittedAtSignal"] <= as_of and row["dateFiled"] <= as_of
        }
        active_keys = set(active_sources)
        if not previous_incremental_source_keys.issubset(active_keys):
            violations.append({"signalMonth": signal_month, "type": "NON_MONOTONE_SOURCE_SET"})
        previous_incremental_source_keys = active_keys

        records = list(base_records)
        seen = set(base_keys)
        incremental_added = 0
        incremental_candidates = 0
        incremental_source_dates = []
        for key, source in sorted(active_sources.items(), key=lambda kv: (kv[1]["dateFiled"], int(kv[1]["cik"]), kv[1]["filename"])):
            if source["dateFiled"] > as_of or source["admittedAtSignal"] > as_of:
                violations.append({"signalMonth": signal_month, "type": "LOOKAHEAD_SOURCE", "source": source})
                continue
            for row in parsed_by_source[key]:
                incremental_candidates += 1
                if row["sourceFilingDate"] > as_of or row["admittedAtSignal"] > as_of:
                    violations.append({"signalMonth": signal_month, "type": "LOOKAHEAD_RECORD", "record": row})
                    continue
                incremental_source_dates.append(row["sourceFilingDate"])
                rkey = record_key(row)
                if rkey in seen:
                    continue
                seen.add(rkey)
                records.append(row)
                incremental_added += 1

        out = {
            "year": 2007,
            "signalMonth": signal_month,
            "asOf": as_of,
            "purpose": "H2 2007 point-in-time N-PX security identity master. Frozen pre-2007 master plus only 2007 N-PX evidence public and admitted by this signal date; no mapping/outcome selection.",
            "baseArtifactId": 9876020712,
            "baseSha256": sha256_file(BASE),
            "baseRecordCount": len(base_records),
            "sampleRule": "Frozen pre-2007 master plus monotone union of each signal date's frozen 64-position equal-quantile sample across earliest primary 2007 N-PX filing per public CIK, plus the fixed 2006 broad-family CIK set when public. No N-Q target-name or performance selection.",
            "activeIncrementalSourceCount": len(active_sources),
            "incrementalParsedRecordCandidates": incremental_candidates,
            "incrementalUniqueRecordsAdded": incremental_added,
            "pairedRecords": sum(bool(r.get("ticker") and r.get("securityId")) for r in records),
            "uniqueRecords": len(records),
            "records": records,
            "incrementalSources": [active_sources[k] for k in sorted(active_sources)],
        }
        out_path = OUT_DIR / f"npx-pit-master-h2-2007-{signal_month}.json"
        out_path.write_text(json.dumps(out, indent=2) + "\n")
        monthly.append({
            "signalMonth": signal_month,
            "asOf": as_of,
            "publicPrimaryFilings": month_selection[signal_month]["publicPrimaryFilings"],
            "publicRepresentativeCiks": month_selection[signal_month]["publicRepresentativeCiks"],
            "selectedUniqueSources": month_selection[signal_month]["selectedUniqueSources"],
            "newAdmissions": month_selection[signal_month]["newAdmissions"],
            "activeIncrementalSources": len(active_sources),
            "incrementalParsedRecordCandidates": incremental_candidates,
            "incrementalUniqueRecordsAdded": incremental_added,
            "totalMasterRecords": len(records),
            "pairedRecords": out["pairedRecords"],
            "maxIncrementalSourceFilingDate": max(incremental_source_dates) if incremental_source_dates else None,
            "output": str(out_path.relative_to(ROOT)),
        })
        print("MONTH", json.dumps(monthly[-1]), flush=True)

    for key, source in admitted.items():
        if source["form"] != "N-PX":
            violations.append({"type": "NON_PRIMARY_ADMISSION", "source": source})
        if source["dateFiled"] > source["admittedAtSignal"]:
            violations.append({"type": "ADMITTED_BEFORE_PUBLIC", "source": source})

    audit = {
        "status": "PASS" if not violations else "FAIL",
        "purpose": "Pre-mapping PIT validation for H2 2007 N-PX identity masters; no N-Q mapping coverage, country, Universe, return, or strategy outcome used.",
        "definition": "docs/research/h2-2007-npx-pit-master-validation-definition.md",
        "baseArtifactId": 9876020712,
        "baseSha256": sha256_file(BASE),
        "baseRecordCount": len(base_records),
        "indexSources": index_sources,
        "inventory": {
            "allNpxAndAmendments": len(filings),
            "primaryNpx": len(primary),
            "npxAmendments": len(amendments),
            "uniquePrimaryCiks": len({x["cik"] for x in primary}),
            "filingMonthCounts": dict(sorted(Counter(x["dateFiled"][:7] for x in filings).items())),
        },
        "broadCiks": sorted(BROAD_CIKS, key=int),
        "admittedSourceCount": len(admitted),
        "fetchErrorCount": 0,
        "sourceResults": source_results,
        "monthly": monthly,
        "violations": violations,
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "status": audit["status"],
        "baseArtifactId": audit["baseArtifactId"],
        "baseSha256": audit["baseSha256"],
        "inventory": audit["inventory"],
        "admittedSourceCount": audit["admittedSourceCount"],
        "fetchErrorCount": audit["fetchErrorCount"],
        "monthly": monthly,
        "violations": violations,
    }), flush=True)
    if violations:
        raise RuntimeError(f"PIT N-PX validation failed with {len(violations)} violation(s)")


if __name__ == "__main__":
    main()
