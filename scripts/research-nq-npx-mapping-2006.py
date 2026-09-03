#!/usr/bin/env python3
from __future__ import annotations

import difflib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NQ = ROOT / "data/research/nq-pit-holdings-2006.json"
NPX = ROOT / "data/research/npx-security-master-2006.json"
OUT = ROOT / "data/research/nq-npx-mapping-2006.json"
BAD_TICKERS = {"N/A", "NA", "NONE", "NULL", "SECURITY", "TICKER", "--", "-"}


def norm(raw: str) -> str:
    s = raw.upper().replace("&", " AND ")
    s = re.sub(r"\b(INCORPORATED|INCORPORATION)\b", "INC", s)
    s = re.sub(r"\b(CORPORATION|CORPORA?TION)\b", "CORP", s)
    s = re.sub(r"\bCOMPANY\b", "CO", s)
    s = re.sub(r"\bLIMITED\b", "LTD", s)
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", s).split())


def edge_the_variants(n: str) -> list[str]:
    out = [n]
    if n.startswith("THE "):
        out.append(n[4:])
    if n.endswith(" THE"):
        out.append(n[:-4])
    return list(dict.fromkeys(x for x in out if x))


def aliases(raw: str) -> list[str]:
    values = [raw]
    stripped = re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", raw, flags=re.I)
    if stripped != raw:
        values.append(stripped)
    out = []
    for value in values:
        for n in edge_the_variants(norm(value)):
            if n and n not in out:
                out.append(n)
    return out


def artifact(raw: str) -> bool:
    n = norm(raw)
    return bool(re.match(r"^(FUND|TOTAL|NET ASSETS?|CASH|SHORT TERM|MONEY MARKET)\b", n) or re.search(r"\bCOST\s+\d", n))


def valid_identity(ticker: str | None, security_id: str | None) -> bool:
    if not ticker or not security_id:
        return False
    t = ticker.upper().strip()
    if t in BAD_TICKERS or "/" in t:
        return False
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", t):
        return False
    return bool(re.fullmatch(r"[A-Z0-9]{8,14}", security_id.upper().strip()))


def ratio(n, d):
    return n / d if d else None


def main() -> None:
    nq, npx = json.loads(NQ.read_text()), json.loads(NPX.read_text())
    by_issuer = defaultdict(set)
    rejected_master_identities = 0
    for row in npx["records"]:
        ticker, security_id = row.get("ticker"), row.get("securityId")
        if not valid_identity(ticker, security_id):
            if ticker or security_id:
                rejected_master_identities += 1
            continue
        for key in edge_the_variants(row["normalizedIssuer"]):
            by_issuer[key].add((ticker, security_id))
    names = sorted(by_issuer)

    total_c = total_w = eligible_c = eligible_w = matched_c = matched_w = amb_c = amb_w = art_c = art_w = 0.0
    details, series = [], []
    for record in nq["records"]:
        rc = rw = mc = mw = ac = aw = pc = pw = 0.0
        for h in record["holdings"]:
            desc, weight = h["description"], float(h.get("weight") or 0)
            total_c += 1; total_w += weight; rc += 1; rw += weight
            ids, matched_alias = [], None
            if artifact(desc):
                status = "PARSER_ARTIFACT"; art_c += 1; art_w += weight; pc += 1; pw += weight
            else:
                eligible_c += 1; eligible_w += weight
                for a in aliases(desc):
                    found = by_issuer.get(a, set())
                    if found:
                        ids, matched_alias = sorted(found), a
                        break
                if len(ids) == 1:
                    status = "MATCHED_UNIQUE"; matched_c += 1; matched_w += weight; mc += 1; mw += weight
                elif len(ids) > 1:
                    status = "AMBIGUOUS"; amb_c += 1; amb_w += weight; ac += 1; aw += weight
                else:
                    status = "UNMAPPED"
            d = {"seriesId": record.get("seriesId"), "fundTickers": record.get("fundTickers", []), "reportDate": record.get("reportDate"), "description": desc, "weight": weight, "normalizedAliases": aliases(desc), "status": status}
            if matched_alias:
                d["matchedAlias"] = matched_alias
            if ids:
                d["identities"] = [{"ticker": t, "securityId": s} for t, s in ids]
            elif status == "UNMAPPED":
                q = aliases(desc)[-1] if aliases(desc) else ""
                d["diagnosticCandidates"] = [{"normalizedIssuer": c, "similarity": difflib.SequenceMatcher(None, q, c).ratio(), "identities": [{"ticker": t, "securityId": s} for t, s in sorted(by_issuer[c])]} for c in difflib.get_close_matches(q, names, n=3, cutoff=.72)]
            details.append(d)
        dc, dw = rc - pc, rw - pw
        series.append({"seriesId": record.get("seriesId"), "seriesName": record.get("seriesName"), "fundTickers": record.get("fundTickers", []), "reportDate": record.get("reportDate"), "holdingCount": int(rc), "eligibleHoldingCount": int(dc), "parserArtifactCount": int(pc), "uniqueMatchedCount": int(mc), "uniqueMatchedCountRate": ratio(mc, dc), "uniqueMatchedWeight": mw, "uniqueMatchedWeightRate": ratio(mw, dw), "ambiguousCount": int(ac), "ambiguousWeight": aw})

    unmapped = [d for d in details if d["status"] == "UNMAPPED"]
    out = {
        "year": 2006,
        "purpose": "Structural validation of N-Q holdings issuer descriptions against deterministic N-PX issuer/ticker/security-id master. No return/performance data used.",
        "mappingRule": "Unique exact match after conservative issuer normalization, trailing N-Q footnote-marker removal, and leading/trailing THE normalization. Fuzzy candidates are diagnostic only and never accepted automatically.",
        "identityQualityRule": "Reject obvious placeholder/invalid N-PX ticker tokens before issuer matching; security ID must be 8-14 alphanumeric characters.",
        "npxSampleRule": npx.get("sampleRule"),
        "npxPairedRecords": npx.get("pairedRecords"),
        "npxUniqueNormalizedIssuers": npx.get("uniqueNormalizedIssuers"),
        "rejectedMasterIdentities": rejected_master_identities,
        "nqPitSeriesRecords": nq.get("pitSeriesRecords"),
        "holdingCount": int(total_c),
        "eligibleHoldingCount": int(eligible_c),
        "eligibleHoldingWeight": eligible_w,
        "parserArtifactCount": int(art_c),
        "parserArtifactWeight": art_w,
        "uniqueMatchedCount": int(matched_c),
        "uniqueMatchedCountRate": ratio(matched_c, eligible_c),
        "uniqueMatchedWeight": matched_w,
        "uniqueMatchedWeightRate": ratio(matched_w, eligible_w),
        "ambiguousCount": int(amb_c),
        "ambiguousWeight": amb_w,
        "unmappedCount": len(unmapped),
        "series": series,
        "topUnmappedByWeight": sorted(unmapped, key=lambda x: x["weight"], reverse=True)[:50],
        "details": details,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k not in {"series", "topUnmappedByWeight", "details"}}), flush=True)
    for row in series:
        print("SERIES", json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
