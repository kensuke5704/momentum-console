#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/research/nq-hybrid-country-resolved-h1-2006.json"
MASTER = ROOT / "data/research/sec-issuer-master-rows-2005-2006.json"
OUT = ROOT / "data/research/country-master-jurisdiction-recovery-v29.json"

US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"
}
JURIS_RE = re.compile(r"\s*/([A-Z0-9]{2,3})/?\s*$", re.I)
FORM_PRIORITY = {"10-K":0,"10-K/A":1,"10-Q":2,"10-Q/A":3,"8-K":4,"8-K/A":5,"DEF 14A":6,"DEFA14A":7,"PRE 14A":8,"11-K":9,"S-8":10,"S-8 POS":11}
ISSUER_FORMS = set(FORM_PRIORITY)


def clean_issuer(s: str) -> str:
    s = re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", s or "", flags=re.I)
    return " ".join(s.replace("’", "'").split()).strip(" .,-")


def normalize_company(s: str) -> str:
    s = JURIS_RE.sub("", s or "")
    s = clean_issuer(s).upper().replace("&", " AND ")
    s = re.sub(r"\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return " ".join(s.split())


def cleaned_forms(raw: str) -> list[str]:
    vals = [raw]
    s = raw
    pats = [
        r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$",
        r"\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$",
        r"\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$",
        r"\s*/[A-Z]{2}\s*$",
    ]
    changed = True
    while changed:
        changed = False
        for p in pats:
            ns = re.sub(p, "", s, flags=re.I).strip()
            if ns != s:
                vals.append(ns)
                s = ns
                changed = True
    return list(dict.fromkeys(v for v in vals if v))


def main() -> None:
    data = json.loads(SRC.read_text())
    master = json.loads(MASTER.read_text())
    rows = master.get("rows", [])
    unknown = [r for r in data.get("resolutionAudit", []) if r.get("classification") == "UNKNOWN"]

    by_norm_date = defaultdict(list)
    for r in rows:
        if r.get("form") not in ISSUER_FORMS:
            continue
        norm = r.get("normalizedCompany") or normalize_company(r.get("company") or "")
        if norm:
            by_norm_date[norm].append(r)

    results = []
    conflicts = []
    suffix_counts = Counter()
    for row in unknown:
        report = row.get("asOfReportDate")
        forms = []
        for issuer in row.get("issuerVariants", []):
            for f in cleaned_forms(str(issuer)):
                if f and f not in forms:
                    forms.append(f)

        exact_rows = []
        ciks = set()
        for form in forms:
            target = normalize_company(form)
            for r in by_norm_date.get(target, []):
                if report and r.get("dateFiled") <= report:
                    exact_rows.append(r)
                    ciks.add(str(r.get("cik") or "").zfill(10))

        rec = {
            "ticker": row.get("ticker"),
            "securityId": row.get("securityId"),
            "asOfReportDate": report,
            "issuerVariants": row.get("issuerVariants", []),
            "historicalExactCikCount": len(ciks),
            "classification": "UNKNOWN",
        }
        if len(ciks) == 1:
            cik = next(iter(ciks))
            rec["historicalExactCik"] = cik
            suffix_evidence = []
            for r in exact_rows:
                if str(r.get("cik") or "").zfill(10) != cik:
                    continue
                m = JURIS_RE.search(r.get("company") or "")
                if not m:
                    continue
                code = m.group(1).upper()
                suffix_evidence.append({
                    "stateCode": code,
                    "company": r.get("company"),
                    "form": r.get("form"),
                    "dateFiled": r.get("dateFiled"),
                    "filename": r.get("filename"),
                    "cik": cik,
                })
            codes = sorted({e["stateCode"] for e in suffix_evidence})
            rec["jurisdictionCodes"] = codes
            rec["evidence"] = suffix_evidence[:20]
            if len(codes) == 1:
                code = codes[0]
                rec.update({
                    "classification": "US" if code in US_CODES else "NON_US",
                    "stateCode": code,
                    "resolutionSource": "PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX",
                    "evidenceDateFiled": max(e["dateFiled"] for e in suffix_evidence),
                })
                suffix_counts[code] += 1
            elif len(codes) > 1:
                conflicts.append({"key":[row.get("ticker"),row.get("securityId"),report],"codes":codes})

        results.append(rec)

    if conflicts:
        raise RuntimeError(f"historical master jurisdiction conflicts: {len(conflicts)}; sample={conflicts[:5]}")

    resolved = [r for r in results if r.get("classification") in {"US","NON_US"}]
    out = {
        "purpose": "Return-independent PIT recovery of strict-country UNKNOWN identities from jurisdiction suffixes embedded in historical SEC master-index company names. Recovery requires cleaned historical issuer exact-name matching to exactly one CIK using only issuer-form rows filed no later than the report date, and exactly one consistent /XX/ or /XXX/ jurisdiction suffix across those matching rows. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.",
        "inputUnknownCount": len(unknown),
        "historicalExactUniqueCikCount": sum(r.get("historicalExactCikCount") == 1 for r in results),
        "resolvedCount": len(resolved),
        "resolvedUSCount": sum(r.get("classification") == "US" for r in resolved),
        "resolvedNonUSCount": sum(r.get("classification") == "NON_US" for r in resolved),
        "remainingUnknownCount": len(unknown) - len(resolved),
        "jurisdictionSuffixCounts": dict(suffix_counts),
        "conflictCount": 0,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("MASTER_JURISDICTION_SUMMARY", json.dumps({k:v for k,v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
