#!/usr/bin/env python3
from __future__ import annotations

import difflib, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NQ = ROOT / "data/research/nq-pit-holdings-2006.json"
NPX = ROOT / "data/research/npx-security-master-2006.json"
OUT = ROOT / "data/research/nq-npx-mapping-2006.json"


def norm(raw: str) -> str:
    s = raw.upper().replace("&", " AND ")
    s = re.sub(r"\b(INCORPORATED|INCORPORATION)\b", "INC", s)
    s = re.sub(r"\b(CORPORATION|CORPORA?TION)\b", "CORP", s)
    s = re.sub(r"\bCOMPANY\b", "CO", s)
    s = re.sub(r"\bLIMITED\b", "LTD", s)
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", s).split())


def aliases(raw: str) -> list[str]:
    # Structural/legal-name variants only. No fuzzy result is ever promoted to
    # an accepted mapping. These transformations are independent of returns.
    s = raw.strip()
    while True:
        stripped = re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", s, flags=re.I)
        if stripped == s:
            break
        s = stripped.strip()
    s = re.sub(r"\s*\(\s*CLASS\s+[A-Z0-9.-]+\s*\)\s*", " ", s, flags=re.I)
    s = re.sub(r"\s+CLASS\s+[A-Z0-9.-]+\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+(?:ADR|GDR)(?:\s*\*+)?\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+\*+\s*$", "", s)

    base = norm(s)
    values = [base]
    no_the = " ".join(t for t in base.split() if t != "THE")
    if no_the:
        values.extend([no_the, f"THE {no_the}", f"{no_the} THE"])
    for value in list(values):
        values.append(re.sub(r"\bCOS\b", "COMPANIES", value))
        values.append(re.sub(r"\bCOMPANIES\b", "COS", value))
        values.append(re.sub(r"\bBANCORPORATION\b", "BANCORP", value))
        values.append(re.sub(r"\bBANCORP\b", "BANCORPORATION", value))

    out = []
    for value in values:
        value = " ".join(value.split())
        if value and value not in out:
            out.append(value)
    return out


def artifact(raw: str) -> bool:
    n = norm(raw)
    return bool(
        re.match(r"^(FUND|TOTAL|NET ASSETS?|CASH|SHORT TERM|MONEY MARKET)\b", n)
        or re.search(r"\bCOST\s+\d", n)
        or re.fullmatch(r"(?:CLASS|SERIES)\s+[A-Z0-9.-]+", n)
    )


def ratio(n, d):
    return n / d if d else None


def main() -> None:
    nq, npx = json.loads(NQ.read_text()), json.loads(NPX.read_text())

    # Tier A requires one unique (ticker, securityId) identity.
    # Tier B is intentionally weaker: no Tier A identity exists, but the same
    # exact normalized issuer maps to one unique ticker in N-PX records where
    # securityId is missing. Multiple tickers remain unresolved.
    tier_a_by_issuer = defaultdict(set)
    ticker_only_by_issuer = defaultdict(set)
    all_tickers_by_issuer = defaultdict(set)
    for row in npx["records"]:
        issuer = row.get("normalizedIssuer") or norm(str(row.get("issuer") or ""))
        ticker = row.get("ticker")
        security_id = row.get("securityId")
        if not issuer or not ticker:
            continue
        all_tickers_by_issuer[issuer].add(ticker)
        if security_id:
            tier_a_by_issuer[issuer].add((ticker, security_id))
        else:
            ticker_only_by_issuer[issuer].add(ticker)

    names = sorted(set(tier_a_by_issuer) | set(ticker_only_by_issuer))

    total_c = total_w = eligible_c = eligible_w = art_c = art_w = 0.0
    a_c = a_w = b_c = b_w = amb_c = amb_w = 0.0
    details, series = [], []

    for record in nq["records"]:
        rc = rw = pc = pw = 0.0
        rac = raw = rbc = rbw = ac = aw = 0.0
        for h in record["holdings"]:
            desc, weight = h["description"], float(h.get("weight") or 0)
            total_c += 1; total_w += weight; rc += 1; rw += weight
            matched_alias = None
            identities = []
            ticker = None

            if artifact(desc):
                status = "PARSER_ARTIFACT"
                art_c += 1; art_w += weight; pc += 1; pw += weight
            else:
                eligible_c += 1; eligible_w += weight
                status = "UNMAPPED"
                for alias in aliases(desc):
                    tier_a = sorted(tier_a_by_issuer.get(alias, set()))
                    if len(tier_a) == 1:
                        status = "TIER_A"
                        matched_alias = alias
                        identities = tier_a
                        break
                    if len(tier_a) > 1:
                        status = "AMBIGUOUS"
                        matched_alias = alias
                        identities = tier_a
                        break

                    # Tier B is permitted only when there is no security-id-backed
                    # identity for this issuer and the issuer has exactly one ticker
                    # across the N-PX master. This prevents ADR/class ambiguity from
                    # being silently promoted.
                    ticker_only = sorted(ticker_only_by_issuer.get(alias, set()))
                    all_tickers = sorted(all_tickers_by_issuer.get(alias, set()))
                    if not tier_a and len(ticker_only) == 1 and len(all_tickers) == 1:
                        status = "TIER_B"
                        matched_alias = alias
                        ticker = ticker_only[0]
                        break
                    if len(ticker_only) > 1 or len(all_tickers) > 1:
                        status = "AMBIGUOUS"
                        matched_alias = alias
                        break

                if status == "TIER_A":
                    a_c += 1; a_w += weight; rac += 1; raw += weight
                elif status == "TIER_B":
                    b_c += 1; b_w += weight; rbc += 1; rbw += weight
                elif status == "AMBIGUOUS":
                    amb_c += 1; amb_w += weight; ac += 1; aw += weight

            d = {
                "seriesId": record.get("seriesId"),
                "fundTickers": record.get("fundTickers", []),
                "reportDate": record.get("reportDate"),
                "description": desc,
                "weight": weight,
                "normalizedAliases": aliases(desc),
                "status": status,
            }
            if matched_alias:
                d["matchedAlias"] = matched_alias
            if identities:
                d["identities"] = [{"ticker": t, "securityId": sid} for t, sid in identities]
            if ticker:
                d["ticker"] = ticker
                d["securityId"] = None
            if status == "UNMAPPED":
                q = aliases(desc)[0] if aliases(desc) else ""
                d["diagnosticCandidates"] = []
                for candidate in difflib.get_close_matches(q, names, n=3, cutoff=.72):
                    a_ids = sorted(tier_a_by_issuer.get(candidate, set()))
                    b_tickers = sorted(ticker_only_by_issuer.get(candidate, set()))
                    d["diagnosticCandidates"].append({
                        "normalizedIssuer": candidate,
                        "similarity": difflib.SequenceMatcher(None, q, candidate).ratio(),
                        "tierAIdentities": [{"ticker": t, "securityId": sid} for t, sid in a_ids],
                        "tickerOnly": b_tickers,
                    })
            details.append(d)

        dc, dw = rc - pc, rw - pw
        series.append({
            "seriesId": record.get("seriesId"),
            "seriesName": record.get("seriesName"),
            "fundTickers": record.get("fundTickers", []),
            "reportDate": record.get("reportDate"),
            "holdingCount": int(rc),
            "eligibleHoldingCount": int(dc),
            "parserArtifactCount": int(pc),
            "tierACount": int(rac),
            "tierACountRate": ratio(rac, dc),
            "tierAWeight": raw,
            "tierAWeightRate": ratio(raw, dw),
            "tierBCount": int(rbc),
            "tierBCountRate": ratio(rbc, dc),
            "tierBWeight": rbw,
            "tierBWeightRate": ratio(rbw, dw),
            "acceptedCount": int(rac + rbc),
            "acceptedCountRate": ratio(rac + rbc, dc),
            "acceptedWeight": raw + rbw,
            "acceptedWeightRate": ratio(raw + rbw, dw),
            "ambiguousCount": int(ac),
            "ambiguousWeight": aw,
        })

    unmapped = [d for d in details if d["status"] == "UNMAPPED"]
    out = {
        "year": 2006,
        "purpose": "Structural validation of N-Q holdings issuer descriptions against deterministic N-PX issuer/ticker/security-id master. No return/performance data used.",
        "mappingRule": "Tier A = unique exact issuer match to one N-PX ticker+securityId identity. Tier B = no Tier A identity and unique exact issuer match to one ticker across N-PX with securityId missing. Structural/legal-name normalization only; fuzzy candidates diagnostic-only; ambiguous identities rejected.",
        "npxSampleRule": npx.get("sampleRule"),
        "npxPairedRecords": npx.get("pairedRecords"),
        "npxUniqueNormalizedIssuers": npx.get("uniqueNormalizedIssuers"),
        "nqPitSeriesRecords": nq.get("pitSeriesRecords"),
        "holdingCount": int(total_c),
        "eligibleHoldingCount": int(eligible_c),
        "eligibleHoldingWeight": eligible_w,
        "parserArtifactCount": int(art_c),
        "parserArtifactWeight": art_w,
        "tierACount": int(a_c),
        "tierACountRate": ratio(a_c, eligible_c),
        "tierAWeight": a_w,
        "tierAWeightRate": ratio(a_w, eligible_w),
        "tierBCount": int(b_c),
        "tierBCountRate": ratio(b_c, eligible_c),
        "tierBWeight": b_w,
        "tierBWeightRate": ratio(b_w, eligible_w),
        "acceptedCount": int(a_c + b_c),
        "acceptedCountRate": ratio(a_c + b_c, eligible_c),
        "acceptedWeight": a_w + b_w,
        "acceptedWeightRate": ratio(a_w + b_w, eligible_w),
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
