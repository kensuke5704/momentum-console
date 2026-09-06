#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/research/nq-hybrid-country-resolved-h1-2006.json"
MASTER = ROOT / "data/research/sec-issuer-master-rows-2005-2006.json"
OUT_TMPL = "country-filing-index-recovery-v29-shard-{shard}.json"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "text/plain,text/html,*/*",
    "Accept-Encoding": "identity",
}
US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"
}
FORM_PRIORITY = {"10-K":0,"10-K/A":1,"10-Q":2,"10-Q/A":3,"8-K":4,"8-K/A":5,"DEF 14A":6,"DEFA14A":7,"PRE 14A":8,"11-K":9,"S-8":10,"S-8 POS":11}
ENTITY_RE = re.compile(r"(?im)^\s*(?:[-*]\s*)?([^\n\r|]{2,180}?)\s+\((?:Filer|Issuer|Reporting|Filed by|Subject)\)\s+CIK:\s*(?:\*\*)?(?:\[)?(\d{1,10})")
STATE_RE = re.compile(r"State\s+of\s+Inc(?:orp)?\.?\s*:\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?", re.I)
JURIS_RE = re.compile(r"\s*/[A-Z0-9]{2,3}/?\s*$", re.I)
PAGE_CACHE: dict[str, tuple[str, str]] = {}


def clean_issuer(s: str) -> str:
    s = re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", s or "", flags=re.I)
    s = re.sub(r"\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*/[A-Z]{2}\s*$", "", s, flags=re.I)
    return " ".join(s.replace("’", "'").split()).strip(" .,-")


def normalize_company(s: str) -> str:
    s = JURIS_RE.sub("", clean_issuer(s)).upper().replace("&", " AND ")
    s = re.sub(r"\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return " ".join(s.split())


def index_url_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    m = re.search(r"edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$", filename, re.I)
    if not m:
        return None
    cik = str(int(m.group(1)))
    acc = m.group(2)
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{acc}-index.html"


def fetch_page(url: str) -> tuple[str, str]:
    if url in PAGE_CACHE:
        return PAGE_CACHE[url]
    last = None
    for candidate in ("https://r.jina.ai/" + url, url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=18) as r:
                text = r.read(800_000).decode("utf-8", "replace")
            PAGE_CACHE[url] = (text, candidate)
            return PAGE_CACHE[url]
        except Exception as exc:
            last = exc
    raise RuntimeError(type(last).__name__ if last else "fetch failed")


def parse_entity_state(text: str, cik: str, issuer_forms: list[str]) -> tuple[str | None, str | None]:
    cleaned = html.unescape(re.sub(r"<[^>]*>", "", text)).replace("\r", "")
    target_names = {normalize_company(x) for x in issuer_forms if normalize_company(x)}
    zcik = str(cik).zfill(10)
    matches = list(ENTITY_RE.finditer(cleaned))
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        if m.group(2).zfill(10) != zcik or normalize_company(name) not in target_names:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else min(len(cleaned), m.end() + 5000)
        states = list(dict.fromkeys(x.upper() for x in STATE_RE.findall(cleaned[m.start():end])))
        if len(states) == 1:
            return states[0], name
    return None, None


def historical_seed(row: dict, master_rows: list[dict]) -> tuple[str | None, list[str], list[dict]]:
    ciks = set()
    forms = []
    for attempt in row.get("attempts", []):
        cik = attempt.get("seedCik")
        if cik:
            ciks.add(str(cik).zfill(10))
        issuer_form = attempt.get("issuerForm")
        if issuer_form and issuer_form not in forms:
            forms.append(issuer_form)
    if len(ciks) != 1 or not forms:
        return None, forms, []
    cik = next(iter(ciks))
    report_date = row.get("asOfReportDate")
    target_names = {normalize_company(x) for x in forms if normalize_company(x)}
    candidates = []
    for r in master_rows:
        if str(r.get("cik") or "").zfill(10) != cik:
            continue
        if r.get("form") not in FORM_PRIORITY:
            continue
        if report_date and r.get("dateFiled") and r["dateFiled"] > report_date:
            continue
        if normalize_company(r.get("company") or "") not in target_names:
            continue
        iu = index_url_from_filename(r.get("filename"))
        if not iu:
            continue
        candidates.append({
            "indexUrl": iu,
            "form": r.get("form"),
            "dateFiled": r.get("dateFiled"),
            "filename": r.get("filename"),
        })
    candidates.sort(key=lambda x: (FORM_PRIORITY.get(x.get("form"), 50), -(int((x.get("dateFiled") or "0000-00-00").replace("-", "") or 0)), x.get("filename") or ""))
    seen = set()
    dedup = []
    for x in candidates:
        if x["indexUrl"] not in seen:
            seen.add(x["indexUrl"])
            dedup.append(x)
    return cik, forms, dedup


def main() -> None:
    shard_i = int(os.environ.get("SHARD_INDEX", "0"))
    shard_n = int(os.environ.get("SHARD_COUNT", "1"))
    data = json.loads(SRC.read_text())
    master = json.loads(MASTER.read_text())
    master_rows = master.get("rows", [])
    if not master_rows:
        raise RuntimeError("Historical SEC master rows are missing")
    all_unknown = sorted(
        [r for r in data.get("resolutionAudit", []) if r.get("classification") == "UNKNOWN"],
        key=lambda r: (r.get("ticker") or "", r.get("securityId") or "", r.get("asOfReportDate") or ""),
    )
    rows = [r for i, r in enumerate(all_unknown) if i % shard_n == shard_i]
    results = []
    counts = Counter()
    fetch_errors = 0
    candidate_rows = 0
    for n, row in enumerate(rows, 1):
        cik, forms, filings = historical_seed(row, master_rows)
        candidate_rows += bool(filings)
        rec = {
            "ticker": row.get("ticker"),
            "securityId": row.get("securityId"),
            "asOfReportDate": row.get("asOfReportDate"),
            "historicalExactCik": cik,
            "issuerForms": forms,
            "candidateFilingCount": len(filings),
            "classification": "UNKNOWN",
            "attempts": [],
        }
        if cik and forms:
            for filing in filings[:6]:
                try:
                    text, transport = fetch_page(filing["indexUrl"])
                    state, entity_name = parse_entity_state(text, cik, forms)
                    rec["attempts"].append({**filing, "transport": transport, "stateCode": state, "historicalEntityName": entity_name})
                    if state:
                        rec.update({
                            "classification": "US" if state in US_CODES else "NON_US",
                            "stateCode": state,
                            "resolutionSource": "PIT_FILING_INDEX_ENTITY_STATE",
                            "historicalEntityName": entity_name,
                            "evidenceForm": filing.get("form"),
                            "evidenceDateFiled": filing.get("dateFiled"),
                            "evidenceFilename": filing.get("filename"),
                            "evidenceIndexUrl": filing.get("indexUrl"),
                            "evidenceTransport": transport,
                        })
                        break
                except Exception as exc:
                    fetch_errors += 1
                    rec["attempts"].append({**filing, "error": type(exc).__name__})
        counts[rec["classification"]] += 1
        results.append(rec)
        if n % 50 == 0:
            print("PROGRESS", json.dumps({"shard": shard_i, "done": n, "counts": dict(counts), "candidateRows": candidate_rows, "fetchErrors": fetch_errors, "pageCache": len(PAGE_CACHE)}), flush=True)
    out = {
        "purpose": "Return-independent PIT recovery of strict-country UNKNOWN identities from ordinary historical SEC filing-detail pages. The historical exact issuer-form -> unique CIK seed is inherited from the accepted strict resolver. Candidate accessions are reconstructed only from the frozen 2005-2006 official SEC master rows using the same CIK, exact normalized historical issuer name, approved issuer form and filing date on or before the report date. Recovery requires the same CIK, matching historical issuer name, and exactly one State of Incorp. value in the same filing-page entity block. Current ticker metadata, fuzzy matching, US default, ranks, returns and strategy outcomes are forbidden.",
        "shardIndex": shard_i,
        "shardCount": shard_n,
        "allInputUnknownCount": len(all_unknown),
        "shardInputUnknownCount": len(rows),
        "candidateInputCount": candidate_rows,
        "resolvedUSCount": counts["US"],
        "resolvedNonUSCount": counts["NON_US"],
        "remainingUnknownCount": counts["UNKNOWN"],
        "fetchErrorCount": fetch_errors,
        "pageCacheCount": len(PAGE_CACHE),
        "results": results,
    }
    path = ROOT / "data/research" / OUT_TMPL.format(shard=shard_i)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
