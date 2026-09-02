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
    # Remove one or more trailing N-Q footnote markers.
    while True:
        stripped = re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", s, flags=re.I)
        if stripped == s:
            break
        s = stripped.strip()
    # Share-class and depositary-receipt labels are security descriptors, not
    # issuer-name content. Security identity is still accepted only if the
    # resulting issuer key maps to exactly one N-PX ticker/security-id pair.
    s = re.sub(r"\s*\(\s*CLASS\s+[A-Z0-9.-]+\s*\)\s*", " ", s, flags=re.I)
    s = re.sub(r"\s+CLASS\s+[A-Z0-9.-]+\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+(?:ADR|GDR)(?:\s*\*+)?\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+\*+\s*$", "", s)

    base = norm(s)
    values = [base]

    # SEC/N-Q sources vary in placement of the non-semantic article "THE".
    no_the = " ".join(t for t in base.split() if t != "THE")
    if no_the:
        values.extend([no_the, f"THE {no_the}", f"{no_the} THE"])

    # Common legacy legal-suffix spelling variants.
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


def ratio(n, d): return n / d if d else None


def main() -> None:
    nq, npx = json.loads(NQ.read_text()), json.loads(NPX.read_text())
    by_issuer = defaultdict(set)
    for row in npx["records"]:
        if row.get("ticker") and row.get("securityId"):
            by_issuer[row["normalizedIssuer"]].add((row["ticker"], row["securityId"]))
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
                    if found: ids, matched_alias = sorted(found), a; break
                if len(ids) == 1:
                    status = "MATCHED_UNIQUE"; matched_c += 1; matched_w += weight; mc += 1; mw += weight
                elif len(ids) > 1:
                    status = "AMBIGUOUS"; amb_c += 1; amb_w += weight; ac += 1; aw += weight
                else: status = "UNMAPPED"
            d = {"seriesId": record.get("seriesId"), "fundTickers": record.get("fundTickers", []), "reportDate": record.get("reportDate"), "description": desc, "weight": weight, "normalizedAliases": aliases(desc), "status": status}
            if matched_alias: d["matchedAlias"] = matched_alias
            if ids: d["identities"] = [{"ticker": t, "securityId": s} for t, s in ids]
            elif status == "UNMAPPED":
                q = aliases(desc)[0] if aliases(desc) else ""
                d["diagnosticCandidates"] = [{"normalizedIssuer": c, "similarity": difflib.SequenceMatcher(None, q, c).ratio(), "identities": [{"ticker": t, "securityId": sid} for t, sid in sorted(by_issuer[c])]} for c in difflib.get_close_matches(q, names, n=3, cutoff=.72)]
            details.append(d)
        dc, dw = rc - pc, rw - pw
        series.append({"seriesId": record.get("seriesId"), "seriesName": record.get("seriesName"), "fundTickers": record.get("fundTickers", []), "reportDate": record.get("reportDate"), "holdingCount": int(rc), "eligibleHoldingCount": int(dc), "parserArtifactCount": int(pc), "uniqueMatchedCount": int(mc), "uniqueMatchedCountRate": ratio(mc, dc), "uniqueMatchedWeight": mw, "uniqueMatchedWeightRate": ratio(mw, dw), "ambiguousCount": int(ac), "ambiguousWeight": aw})

    unmapped = [d for d in details if d["status"] == "UNMAPPED"]
    out = {"year": 2006, "purpose": "Structural validation of N-Q holdings issuer descriptions against deterministic N-PX issuer/ticker/security-id master. No return/performance data used.", "mappingRule": "Unique exact match after conservative issuer/legal-name normalization (footnotes, class labels, ADR/GDR labels, THE placement, common legal suffix spelling). Fuzzy candidates are diagnostic only and never accepted automatically.", "npxSampleRule": npx.get("sampleRule"), "npxPairedRecords": npx.get("pairedRecords"), "npxUniqueNormalizedIssuers": npx.get("uniqueNormalizedIssuers"), "nqPitSeriesRecords": nq.get("pitSeriesRecords"), "holdingCount": int(total_c), "eligibleHoldingCount": int(eligible_c), "eligibleHoldingWeight": eligible_w, "parserArtifactCount": int(art_c), "parserArtifactWeight": art_w, "uniqueMatchedCount": int(matched_c), "uniqueMatchedCountRate": ratio(matched_c, eligible_c), "uniqueMatchedWeight": matched_w, "uniqueMatchedWeightRate": ratio(matched_w, eligible_w), "ambiguousCount": int(amb_c), "ambiguousWeight": amb_w, "unmappedCount": len(unmapped), "series": series, "topUnmappedByWeight": sorted(unmapped, key=lambda x: x["weight"], reverse=True)[:50], "details": details}
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k not in {"series", "topUnmappedByWeight", "details"}}), flush=True)
    for row in series: print("SERIES", json.dumps(row), flush=True)

if __name__ == "__main__": main()
