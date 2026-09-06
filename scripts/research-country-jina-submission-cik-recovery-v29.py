#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.request
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
SRC = R / "nq-hybrid-country-resolved-h1-2006.json"
MASTER = R / "sec-issuer-master-rows-2005-2006.json"
UA = {"User-Agent": "momentum-console historical research kensuke5704@users.noreply.github.com", "Accept": "text/plain,*/*"}
US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"
}
FORMS = {"10-K","10-K/A","10-Q","10-Q/A","8-K","8-K/A","DEF 14A","DEFA14A","PRE 14A","11-K","S-8","S-8 POS"}
FORM_PRIORITY = {"10-K":0,"10-K/A":1,"10-Q":2,"10-Q/A":3,"8-K":4,"8-K/A":5,"DEF 14A":6,"DEFA14A":7,"PRE 14A":8,"11-K":9,"S-8":10,"S-8 POS":11}


def exact_key(ticker, security_id, report_date):
    return ((ticker or "").strip().upper(), security_id or None, report_date or None)


def seed_cik(row: dict) -> str | None:
    ciks = set()
    for attempt in row.get("attempts", []):
        if int(attempt.get("historicalExactCikCount") or 0) == 1 and attempt.get("seedCik"):
            ciks.add(str(attempt["seedCik"]).zfill(10))
    return next(iter(ciks)) if len(ciks) == 1 else None


def filing_sort_key(row: dict):
    # Most recent pre-report filing first; form priority only breaks same-date ties.
    return (-int(row["dateFiled"].replace("-", "")), FORM_PRIORITY.get(row.get("form"), 99), row.get("filename") or "")


def fetch_jina_submission(filename: str) -> tuple[str, str]:
    native = "https://www.sec.gov/Archives/" + filename.lstrip("/")
    url = "https://r.jina.ai/" + native
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as response:
        # Header is at the beginning. Bound memory/network even if Jina renders a large filing.
        data = response.read(900_000)
    return data.decode("utf-8", "replace"), url


def state_for_cik(text: str, cik: str) -> tuple[str | None, str | None]:
    zcik = str(cik).zfill(10)
    # Accept both old flat SEC-HEADER and SGML COMPANY-DATA grammars, but identity is CIK-only.
    header = text.split("</SEC-HEADER>", 1)[0]
    blocks = re.split(r"(?im)^\s*COMPANY\s+DATA\s*:\s*$", header)
    for block in blocks[1:]:
        part = re.split(r"(?im)^\s*(?:FILING\s+VALUES|BUSINESS\s+ADDRESS|MAIL\s+ADDRESS|FORMER\s+COMPANY)\s*:\s*$", block, maxsplit=1)[0]
        ck = re.search(r"(?im)^\s*CENTRAL\s+INDEX\s+KEY\s*:\s*(\d{1,10})\s*$", part)
        st = re.search(r"(?im)^\s*STATE\s+OF\s+INCORPORATION\s*:\s*([A-Z0-9]{2,3})\s*$", part)
        nm = re.search(r"(?im)^\s*COMPANY\s+CONFORMED\s+NAME\s*:\s*(.+?)\s*$", part)
        if ck and ck.group(1).zfill(10) == zcik and st:
            return st.group(1).upper(), nm.group(1).strip() if nm else None

    for m in re.finditer(r"<COMPANY-DATA>(.*?)(?=<FILING-VALUES>|<BUSINESS-ADDRESS>|<MAIL-ADDRESS>|<FORMER-COMPANY>|</FILER>|</ISSUER>|$)", header, re.I | re.S):
        block = m.group(1)
        ck = re.search(r"<CIK>\s*(\d{1,10})", block, re.I)
        st = re.search(r"<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})", block, re.I)
        nm = re.search(r"<CONFORMED-NAME>\s*([^\r\n<]+)", block, re.I)
        if ck and ck.group(1).zfill(10) == zcik and st:
            return st.group(1).upper(), nm.group(1).strip() if nm else None
    return None, None


def main() -> None:
    shard_i = int(os.environ.get("SHARD_INDEX", "0"))
    shard_n = int(os.environ.get("SHARD_COUNT", "1"))
    country = json.loads(SRC.read_text())
    master = json.loads(MASTER.read_text())

    unknown = [r for r in country.get("resolutionAudit", []) if r.get("classification") == "UNKNOWN"]
    grouped = defaultdict(list)
    for row in unknown:
        cik = seed_cik(row)
        if cik:
            grouped[cik].append(row)
    seeds = sorted(grouped)
    my_seeds = [c for i, c in enumerate(seeds) if i % shard_n == shard_i]

    by_cik = defaultdict(list)
    for row in master.get("rows", []):
        cik = str(row.get("cik") or "").zfill(10)
        if row.get("form") in FORMS and cik:
            by_cik[cik].append(row)

    results = []
    fetched = 0
    errors = 0
    resolved = Counter()
    cache: dict[str, tuple[str | None, str | None, str | None, str | None]] = {}

    for idx, cik in enumerate(my_seeds, 1):
        queries = grouped[cik]
        for query in queries:
            report = query.get("asOfReportDate")
            candidates = sorted(
                [r for r in by_cik.get(cik, []) if report and r.get("dateFiled") <= report],
                key=filing_sort_key,
            )[:6]
            rec = {
                "ticker": query.get("ticker"),
                "securityId": query.get("securityId"),
                "asOfReportDate": report,
                "issuerVariants": query.get("issuerVariants", []),
                "historicalExactCik": cik,
                "classification": "UNKNOWN",
                "attempts": [],
            }
            for filing in candidates:
                fn = filing.get("filename")
                if not fn:
                    continue
                if fn not in cache:
                    try:
                        text, transport = fetch_jina_submission(fn)
                        state, historical_name = state_for_cik(text, cik)
                        cache[fn] = (state, historical_name, transport, None)
                        fetched += 1
                    except Exception as exc:
                        cache[fn] = (None, None, None, type(exc).__name__)
                        errors += 1
                state, historical_name, transport, error = cache[fn]
                one = {
                    "form": filing.get("form"),
                    "dateFiled": filing.get("dateFiled"),
                    "filename": fn,
                    "stateCode": state,
                    "historicalEntityName": historical_name,
                    "transport": transport,
                    "error": error,
                }
                rec["attempts"].append(one)
                if state:
                    rec.update({
                        "classification": "US" if state in US_CODES else "NON_US",
                        "stateCode": state,
                        "resolutionSource": "PIT_JINA_SUBMISSION_HEADER_UNIQUE_HISTORICAL_CIK_STATE",
                        "historicalEntityName": historical_name,
                        "evidenceForm": filing.get("form"),
                        "evidenceDateFiled": filing.get("dateFiled"),
                        "evidenceFilename": fn,
                        "evidenceTransport": transport,
                    })
                    resolved[rec["classification"]] += 1
                    break
            results.append(rec)
        if idx % 20 == 0:
            print("PROGRESS", json.dumps({"shard":shard_i,"ciksDone":idx,"queryRows":len(results),"resolved":dict(resolved),"fetched":fetched,"errors":errors}), flush=True)

    out = {
        "purpose": "Return-independent PIT country recovery for original strict UNKNOWNs. Historical issuer exact-name matching must already have produced exactly one CIK. Country is then read from a pre-report-date SEC complete-submission header by matching that same CIK only. Jina is transport only. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.",
        "shardIndex": shard_i,
        "shardCount": shard_n,
        "allInputUnknownCount": len(unknown),
        "allHistoricalExactUniqueCikCount": len(seeds),
        "allHistoricalExactUniqueCikQueryCount": sum(len(v) for v in grouped.values()),
        "shardCikCount": len(my_seeds),
        "shardInputQueryCount": sum(len(grouped[c]) for c in my_seeds),
        "resolvedUSCount": resolved["US"],
        "resolvedNonUSCount": resolved["NON_US"],
        "remainingUnknownCount": len(results) - resolved["US"] - resolved["NON_US"],
        "successfulFetchCount": fetched,
        "transportErrorCount": errors,
        "results": results,
    }
    out_path = R / f"country-jina-submission-cik-recovery-v29-shard-{shard_i}.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k:v for k,v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
