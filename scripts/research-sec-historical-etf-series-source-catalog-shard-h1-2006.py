#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/research/sec-marketwide-nq-inventory-h1-2006.json"
PREF = ROOT / "data/research/sec-etf-registrant-operational-prefilter-h1-2006.json"
SHARD_INDEX = int(os.environ.get("SHARD_INDEX", "0"))
SHARD_COUNT = int(os.environ.get("SHARD_COUNT", "1"))
OUT = ROOT / f"data/research/sec-historical-etf-series-source-catalog-h1-2006-shard-{SHARD_INDEX:02d}.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load_module("catalog_base", ROOT / "scripts/research-sec-historical-etf-series-source-catalog-h1-2006.py")


def complete_prospectus_set(rows: list[dict]) -> list[dict]:
    """Source-complete deterministic prospectus set without outcome-based selection.

    Every core registration/prospectus filing is retained because mixed trusts may file
    separate core amendments for different Series in the same month. For 497 supplements,
    retain the latest public filing per month because supplements are high-volume and the
    validated operational structure should ordinarily be present in core filings.
    """
    chosen: dict[str, dict] = {}
    for row in rows:
        if row["form"] in base.CORE:
            chosen[row["filename"]] = row
    for month, asof in base.MONTHS:
        avail = [
            row for row in rows
            if row["form"] in base.SUPP and row["dateFiled"] <= asof and row["dateFiled"].startswith(month)
        ]
        if avail:
            latest = max(avail, key=lambda row: (row["dateFiled"], row["form"], row["filename"]))
            chosen[latest["filename"]] = latest
    return sorted(chosen.values(), key=lambda row: (row["dateFiled"], row["form"], row["filename"]))


def main() -> None:
    if SHARD_COUNT < 1 or not 0 <= SHARD_INDEX < SHARD_COUNT:
        raise ValueError("invalid shard configuration")
    inv = json.loads(INV.read_text())
    pref = json.loads(PREF.read_text())
    all_ciks = sorted(pref["positiveCiks"])
    selected = [cik for i, cik in enumerate(all_ciks) if i % SHARD_COUNT == SHARD_INDEX]
    pros, master_transports = base.load_prospectus(set(selected))

    evidence = []
    prospectus_diagnostics = []
    for cik in selected:
        rows = complete_prospectus_set(pros.get(cik, []))
        for filing in rows:
            rec = {
                **filing,
                "indexUrl": base.iu(filing["filename"]),
                "submissionUrl": base.su(filing["filename"]),
            }
            try:
                series, index_transport, index_prior = base.parse_index_series(rec["indexUrl"])
                rec["indexTransport"] = index_transport
                rec["indexPriorErrors"] = index_prior
                rec["indexSeriesCount"] = len(series)
                text, submission_transport, _, submission_prior = base.ft(rec["submissionUrl"], 4_000_000, 22)
                rec["submissionTransport"] = submission_transport
                rec["submissionPriorErrors"] = submission_prior
                creation = base.rule.find(base.rule.CREATION, text)
                exchange = base.rule.find(base.rule.EXCHANGE, text)
                rec["creationIssuerOwnEvidence"] = bool(creation)
                rec["exchangeIssuerOwnEvidence"] = bool(exchange)
                ctxnorm = base.norm(base.context(text, creation, exchange))
                positive = []
                if creation and exchange:
                    for series_row in series:
                        explicit = any(
                            base.EXPLICIT_ETF_CLASS.search(x.get("className") or "")
                            for x in series_row["classes"]
                        )
                        local = bool(
                            series_row["seriesName"]
                            and base.norm(series_row["seriesName"])
                            and base.norm(series_row["seriesName"]) in ctxnorm
                        )
                        single = len(series) == 1
                        if not (single or local or explicit):
                            continue
                        positive.append({
                            "cik": cik,
                            "seriesId": series_row["seriesId"],
                            "seriesName": series_row["seriesName"],
                            "evidenceDateFiled": filing["dateFiled"],
                            "evidenceForm": filing["form"],
                            "evidenceFilename": filing["filename"],
                            "binding": (
                                "SINGLE_SERIES_FILING" if single
                                else "LOCAL_SERIES_NAME" if local
                                else "EXPLICIT_ETF_CLASS"
                            ),
                        })
                rec["positiveSeriesCount"] = len(positive)
                evidence.extend(positive)
            except Exception as exc:
                rec["error"] = type(exc).__name__
                rec["errorDetail"] = str(exc)[:900]
            prospectus_diagnostics.append(rec)
            print(
                "PROSPECTUS",
                json.dumps({
                    "shard": SHARD_INDEX,
                    "cik": cik,
                    "form": filing["form"],
                    "dateFiled": filing["dateFiled"],
                    "series": rec.get("indexSeriesCount"),
                    "creation": rec.get("creationIssuerOwnEvidence"),
                    "exchange": rec.get("exchangeIssuerOwnEvidence"),
                    "positive": rec.get("positiveSeriesCount"),
                    "error": rec.get("error"),
                }),
                flush=True,
            )

    first = {}
    for row in sorted(evidence, key=lambda x: (x["evidenceDateFiled"], x["seriesId"], x["evidenceFilename"])):
        if row["seriesId"] not in first:
            first[row["seriesId"]] = row
    positive_series = list(first.values())
    positive_ids = set(first)

    nq_rows = []
    nq_diagnostics = []
    selected_set = set(selected)
    for row in [x for x in inv["rows"] if x["cik"] in selected_set]:
        rec = {k: row[k] for k in ("cik", "company", "form", "dateFiled", "filename", "accession", "indexUrl")}
        try:
            series, transport, prior = base.parse_index_series(row["indexUrl"])
            rec["transport"] = transport
            rec["priorErrors"] = prior
            rec["seriesCount"] = len(series)
            rec["positiveSeriesIds"] = [s["seriesId"] for s in series if s["seriesId"] in positive_ids]
            for series_row in series:
                if series_row["seriesId"] not in positive_ids:
                    continue
                nq_rows.append({
                    **row,
                    "seriesId": series_row["seriesId"],
                    "seriesName": series_row["seriesName"] or first[series_row["seriesId"]]["seriesName"],
                })
        except Exception as exc:
            rec["error"] = type(exc).__name__
            rec["seriesCount"] = 0
            rec["positiveSeriesIds"] = []
        nq_diagnostics.append(rec)

    dedup = {}
    for row in nq_rows:
        dedup[(row["seriesId"], row["accession"])] = row
    nq_rows = list(dedup.values())

    out = {
        "purpose": (
            "Shard of the source-complete H1 2006 strict ETF Series-ID evidence scan. Candidate CIKs are "
            "partitioned deterministically. Every core 485/N-1A prospectus/registration filing through "
            "2006-06-30 plus the latest 497 supplement in each filing month is inspected. Final Series-ID "
            "binding still requires validated issuer-own Creation Unit plus exchange evidence and structural "
            "filing-index binding. No holdings outcomes, ranks, returns, or strategy results are used."
        ),
        "shardIndex": SHARD_INDEX,
        "shardCount": SHARD_COUNT,
        "candidateRegistrantCount": len(all_ciks),
        "selectedRegistrantCount": len(selected),
        "selectedCiks": selected,
        "prospectusInspectedCount": len(prospectus_diagnostics),
        "prospectusErrorCount": sum("error" in x for x in prospectus_diagnostics),
        "prospectusEvidenceRecordCount": len(evidence),
        "positiveSeriesCount": len(positive_series),
        "positiveSeries": sorted(positive_series, key=lambda x: x["seriesId"]),
        "nqPositiveSeriesFilingCount": len(nq_rows),
        "nqPositiveSeriesFilings": sorted(nq_rows, key=lambda x: (x["seriesId"], x["dateFiled"], x["accession"])),
        "nqIndexErrorCount": sum("error" in x for x in nq_diagnostics),
        "masterTransports": master_transports,
        "prospectusDiagnostics": prospectus_diagnostics,
        "nqDiagnostics": nq_diagnostics,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(
        "SUMMARY",
        json.dumps({
            "shardIndex": SHARD_INDEX,
            "selectedRegistrantCount": len(selected),
            "prospectusInspectedCount": len(prospectus_diagnostics),
            "prospectusErrorCount": out["prospectusErrorCount"],
            "positiveSeriesCount": len(positive_series),
            "nqPositiveSeriesFilingCount": len(nq_rows),
            "nqIndexErrorCount": out["nqIndexErrorCount"],
        }),
        flush=True,
    )


if __name__ == "__main__":
    main()
