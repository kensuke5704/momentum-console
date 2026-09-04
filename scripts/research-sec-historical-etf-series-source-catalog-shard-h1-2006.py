#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
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
    separate core amendments for different Series in the same month. For high-volume 497
    supplements, retain the latest filing available at each H1 month end; deduplication
    naturally carries a late-2005 supplement into January when it is still the latest.
    """
    chosen: dict[str, dict] = {}
    for row in rows:
        if row["form"] in base.CORE:
            chosen[row["filename"]] = row
    for _, asof in base.MONTHS:
        avail = [row for row in rows if row["form"] in base.SUPP and row["dateFiled"] <= asof]
        if avail:
            latest = max(avail, key=lambda row: (row["dateFiled"], row["form"], row["filename"]))
            chosen[latest["filename"]] = latest
    return sorted(chosen.values(), key=lambda row: (row["dateFiled"], row["form"], row["filename"]))


def evidence_sort_key(row: dict) -> tuple[str, str, str]:
    return row["evidenceDateFiled"], row["seriesId"], row["evidenceFilename"]


def maybe_keep_earlier(target: dict[str, dict], candidate: dict) -> None:
    sid = candidate["seriesId"]
    current = target.get(sid)
    if current is None or evidence_sort_key(candidate) < evidence_sort_key(current):
        target[sid] = candidate


def main() -> None:
    if SHARD_COUNT < 1 or not 0 <= SHARD_INDEX < SHARD_COUNT:
        raise ValueError("invalid shard configuration")
    inv = json.loads(INV.read_text())
    pref = json.loads(PREF.read_text())
    all_ciks = sorted(pref["positiveCiks"])
    selected = [cik for i, cik in enumerate(all_ciks) if i % SHARD_COUNT == SHARD_INDEX]
    pros, master_transports = base.load_prospectus(set(selected))

    directly_bound_evidence = []
    operational_by_cik: dict[str, list[dict]] = defaultdict(list)
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
                    operational_by_cik[cik].append({
                        "dateFiled": filing["dateFiled"],
                        "form": filing["form"],
                        "filename": filing["filename"],
                        "contextNorm": ctxnorm,
                        "prospectusIndexSeriesCount": len(series),
                    })
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
                            "operationalEvidenceDateFiled": filing["dateFiled"],
                            "seriesMetadataDateFiled": filing["dateFiled"],
                            "evidenceForm": filing["form"],
                            "evidenceFilename": filing["filename"],
                            "binding": (
                                "PROSPECTUS_SINGLE_SERIES" if single
                                else "PROSPECTUS_LOCAL_SERIES_NAME" if local
                                else "PROSPECTUS_EXPLICIT_ETF_CLASS"
                            ),
                        })
                rec["positiveSeriesCount"] = len(positive)
                directly_bound_evidence.extend(positive)
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

    first: dict[str, dict] = {}
    for row in sorted(directly_bound_evidence, key=evidence_sort_key):
        maybe_keep_earlier(first, row)

    # Some pre-2006 SEC prospectus index pages expose no Series/Class table even though the
    # filing itself contains issuer-own Creation Unit + exchange evidence. In that case,
    # bind only when contemporaneously public N-Q index metadata supplies either:
    #   (a) an explicit ETF/VIPER class for the Series, or
    #   (b) the exact normalized Series name inside the local operational-evidence context.
    # The binding becomes public only when BOTH ingredients are public, so the effective
    # evidenceDateFiled is max(prospectus date, N-Q metadata filing date). This prevents
    # later Series metadata from being backfilled into an earlier PIT month.
    nq_diagnostics = []
    parsed_nq = []
    selected_set = set(selected)
    for row in [x for x in inv["rows"] if x["cik"] in selected_set]:
        rec = {k: row[k] for k in ("cik", "company", "form", "dateFiled", "filename", "accession", "indexUrl")}
        try:
            series, transport, prior = base.parse_index_series(row["indexUrl"])
            rec["transport"] = transport
            rec["priorErrors"] = prior
            rec["seriesCount"] = len(series)
            parsed_nq.append((row, series))

            fallback_ids = []
            ops = sorted(
                operational_by_cik.get(row["cik"], []),
                key=lambda x: (x["dateFiled"], x["filename"]),
            )
            for series_row in series:
                sid = series_row["seriesId"]
                sname = series_row.get("seriesName") or ""
                sname_norm = base.norm(sname)
                explicit_class = any(
                    base.EXPLICIT_ETF_CLASS.search(x.get("className") or "")
                    for x in series_row.get("classes", [])
                )
                candidates = []
                for op in ops:
                    local_name = bool(sname_norm and sname_norm in op["contextNorm"])
                    if not explicit_class and not local_name:
                        continue
                    binding_public = max(op["dateFiled"], row["dateFiled"])
                    candidates.append({
                        "cik": row["cik"],
                        "seriesId": sid,
                        "seriesName": sname,
                        "evidenceDateFiled": binding_public,
                        "operationalEvidenceDateFiled": op["dateFiled"],
                        "seriesMetadataDateFiled": row["dateFiled"],
                        "evidenceForm": op["form"],
                        "evidenceFilename": op["filename"],
                        "binding": (
                            "NQ_EXPLICIT_ETF_CLASS_PLUS_ISSUER_OWN_EVIDENCE"
                            if explicit_class
                            else "NQ_LOCAL_SERIES_NAME_PLUS_ISSUER_OWN_EVIDENCE"
                        ),
                    })
                if candidates:
                    candidate = min(candidates, key=evidence_sort_key)
                    before = first.get(sid)
                    maybe_keep_earlier(first, candidate)
                    if before is None or first.get(sid) is candidate:
                        fallback_ids.append(sid)
            rec["fallbackBoundSeriesIds"] = sorted(set(fallback_ids))
        except Exception as exc:
            rec["error"] = type(exc).__name__
            rec["seriesCount"] = 0
            rec["fallbackBoundSeriesIds"] = []
        nq_diagnostics.append(rec)

    positive_series = sorted(first.values(), key=lambda x: x["seriesId"])
    positive_ids = set(first)

    nq_rows = []
    positive_by_accession: dict[str, list[str]] = defaultdict(list)
    for row, series in parsed_nq:
        for series_row in series:
            sid = series_row["seriesId"]
            if sid not in positive_ids:
                continue
            positive_by_accession[row["accession"]].append(sid)
            nq_rows.append({
                **row,
                "seriesId": sid,
                "seriesName": series_row["seriesName"] or first[sid]["seriesName"],
            })
    for rec in nq_diagnostics:
        rec["positiveSeriesIds"] = sorted(set(positive_by_accession.get(rec["accession"], [])))

    dedup = {}
    for row in nq_rows:
        dedup[(row["seriesId"], row["accession"])] = row
    nq_rows = list(dedup.values())

    fallback_count = sum(
        row["binding"].startswith("NQ_") for row in positive_series
    )
    out = {
        "purpose": (
            "Shard of the source-complete H1 2006 strict ETF Series-ID evidence scan. Candidate CIKs are "
            "partitioned deterministically. Every core 485/N-1A prospectus/registration filing through "
            "2006-06-30 plus the latest 497 available at each H1 month end is inspected. Final Series-ID "
            "binding requires validated issuer-own Creation Unit plus exchange evidence. When an older "
            "prospectus index exposes no Series/Class table, contemporaneously public N-Q metadata may bridge "
            "the Series only via an explicit ETF/VIPER class or exact Series name inside the local operational "
            "evidence context; the effective binding date is the later of the two filings. No holdings outcomes, "
            "ranks, returns, or strategy results are used."
        ),
        "shardIndex": SHARD_INDEX,
        "shardCount": SHARD_COUNT,
        "candidateRegistrantCount": len(all_ciks),
        "selectedRegistrantCount": len(selected),
        "selectedCiks": selected,
        "prospectusInspectedCount": len(prospectus_diagnostics),
        "prospectusErrorCount": sum("error" in x for x in prospectus_diagnostics),
        "prospectusDirectEvidenceRecordCount": len(directly_bound_evidence),
        "issuerOwnOperationalFilingCount": sum(len(x) for x in operational_by_cik.values()),
        "positiveSeriesCount": len(positive_series),
        "nqFallbackPositiveSeriesCount": fallback_count,
        "positiveSeries": positive_series,
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
            "issuerOwnOperationalFilingCount": out["issuerOwnOperationalFilingCount"],
            "positiveSeriesCount": len(positive_series),
            "nqFallbackPositiveSeriesCount": fallback_count,
            "nqPositiveSeriesFilingCount": len(nq_rows),
            "nqIndexErrorCount": out["nqIndexErrorCount"],
        }),
        flush=True,
    )


if __name__ == "__main__":
    main()
