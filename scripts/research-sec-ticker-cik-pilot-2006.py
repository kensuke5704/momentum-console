#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "research" / "sec-ticker-cik-pilot-2006.json"
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "text/plain,text/html,*/*"}

# Fixed structural sample: active and delisted/acquired 2006-era securities.
# Selection is independent of Momentum returns/universe rank.
SAMPLE = [
    {"ticker": "ABT", "issuer": "ABBOTT LABORATORIES", "statusClass": "ACTIVE"},
    {"ticker": "MSFT", "issuer": "MICROSOFT CORP", "statusClass": "ACTIVE"},
    {"ticker": "SAP", "issuer": "SAP AG", "statusClass": "ACTIVE_FOREIGN"},
    {"ticker": "BP", "issuer": "BP PLC", "statusClass": "ACTIVE_FOREIGN"},
    {"ticker": "REY", "issuer": "REYNOLDS & REYNOLDS CO", "statusClass": "DELISTED_ACQUIRED"},
    {"ticker": "SVU", "issuer": "SUPERVALU INC", "statusClass": "DELISTED_ACQUIRED"},
    {"ticker": "LEH", "issuer": "LEHMAN BROTHERS HOLDINGS INC", "statusClass": "DELISTED_BANKRUPT"},
]

ARCHIVE_CIK_RE = re.compile(r"/Archives/edgar/data/(\d+)/", re.I)
ARCHIVE_RE = re.compile(r"https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"'<>\)]+", re.I)
STATE_RE = re.compile(r"State\s+of\s+Inc(?:orp)?\.?:\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?\b", re.I)
CANDIDATE_ROW_RE = re.compile(r"\|\s*\[(\d{10})\]\([^\)]*CIK=\1[^\)]*\)\s*\|\s*([^|]+?)\s*\|", re.I)
US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"
}


def get(url: str, timeout: int = 10) -> tuple[str, str, int]:
    last = None
    for candidate in ("https://r.jina.ai/" + url, url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(2_000_000)
            return raw.decode("utf-8", "replace"), candidate, len(raw)
        except Exception as e:
            last = repr(e)
    raise RuntimeError(last or "fetch failed")


def sec_url(params: dict[str, str]) -> str:
    return "https://www.sec.gov/cgi-bin/browse-edgar?" + urllib.parse.urlencode(params)


def normalize_name(s: str) -> str:
    s = re.sub(r"\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD)\b", " ", s.upper())
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return " ".join(s.split())


def parse_browse(url: str) -> dict:
    text, transport, nbytes = get(url)
    urls = list(dict.fromkeys(ARCHIVE_RE.findall(text)))
    ciks = list(dict.fromkeys(m.group(1).zfill(10) for u in urls for m in [ARCHIVE_CIK_RE.search(u)] if m))
    states = list(dict.fromkeys(x.upper() for x in STATE_RE.findall(text)))
    candidates = []
    for cik, raw_name in CANDIDATE_ROW_RE.findall(text):
        name = re.sub(r"\s+SIC:.*$", "", raw_name.strip(), flags=re.I)
        candidates.append({"cik": cik, "name": name, "normalizedName": normalize_name(name)})
    return {"url": url, "transport": transport, "bytes": nbytes, "archiveUrls": urls[:12], "ciksFromArchive": ciks, "stateCodesOnBrowse": states, "companyCandidates": candidates[:20], "snippet": " ".join(text.split())[:1100]}


def browse_by_ticker(ticker: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","CIK":ticker,"type":"","dateb":"20061231","owner":"exclude","count":"40"}))


def browse_by_issuer(issuer: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","company":issuer,"type":"","dateb":"20061231","owner":"exclude","count":"40"}))


def browse_by_cik(cik: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","CIK":cik,"type":"","dateb":"20061231","owner":"exclude","count":"40"}))


def inspect_index(url: str) -> dict:
    text, transport, nbytes = get(url)
    states = list(dict.fromkeys(x.upper() for x in STATE_RE.findall(text)))
    return {"url": url, "transport": transport, "bytes": nbytes, "stateCodes": states, "snippet": " ".join(text.split())[:700]}


def resolve_from_browse(browse: dict) -> tuple[str | None, list[dict]]:
    attempts = []
    for url in browse.get("archiveUrls", [])[:6]:
        try:
            idx = inspect_index(url)
        except Exception as e:
            idx = {"url": url, "error": repr(e), "stateCodes": []}
        attempts.append(idx)
        if idx.get("stateCodes"):
            return idx["stateCodes"][0], attempts
        time.sleep(0.15)
    if browse.get("stateCodesOnBrowse"):
        return browse["stateCodesOnBrowse"][0], attempts
    return None, attempts


def candidate_fallback(issuer: str, issuer_browse: dict) -> tuple[dict | None, list[dict]]:
    target = normalize_name(issuer)
    candidates = issuer_browse.get("companyCandidates", [])
    exact = [c for c in candidates if c["normalizedName"] == target]
    pool = exact if exact else candidates
    audits = []
    viable = []
    for c in pool[:8]:
        try:
            b = browse_by_cik(c["cik"])
            audit = {**c, "archiveCount": len(b.get("archiveUrls", [])), "stateCodesOnBrowse": b.get("stateCodesOnBrowse", [])}
            audits.append(audit)
            if b.get("archiveUrls"):
                viable.append((c, b))
        except Exception as e:
            audits.append({**c, "error": repr(e)})
        time.sleep(0.15)
    # Conservative acceptance: exactly one candidate with filings no later than 2006-12-31.
    if len(viable) == 1:
        c, b = viable[0]
        return {"candidate": c, "browse": b}, audits
    return None, audits


def main() -> None:
    rows = []
    for item in SAMPLE:
        row = {**item}
        try:
            ticker_browse = browse_by_ticker(item["ticker"])
            row["tickerBrowse"] = ticker_browse
            source = "TICKER"
            browse = ticker_browse
            if not browse.get("archiveUrls"):
                issuer_browse = browse_by_issuer(item["issuer"])
                row["issuerBrowse"] = issuer_browse
                if issuer_browse.get("archiveUrls") and len(issuer_browse.get("ciksFromArchive", [])) == 1:
                    source = "ISSUER_DIRECT_SINGLE_CIK"
                    browse = issuer_browse
                elif issuer_browse.get("companyCandidates"):
                    resolved_candidate, audits = candidate_fallback(item["issuer"], issuer_browse)
                    row["issuerCandidateAudits"] = audits
                    if resolved_candidate:
                        source = "ISSUER_CANDIDATE_SINGLE_PIT_CIK"
                        row["issuerCandidateResolved"] = resolved_candidate["candidate"]
                        browse = resolved_candidate["browse"]
            state, attempts = resolve_from_browse(browse)
            row["historicalFilingAttempts"] = attempts
            if browse.get("archiveUrls") and len(browse.get("ciksFromArchive", [])) == 1:
                row["resolvedCik"] = browse["ciksFromArchive"][0]
            if state:
                row["resolvedStateCode"] = state
                row["resolvedUS"] = state in US_CODES
                row["resolutionSource"] = source
        except Exception as e:
            row["error"] = repr(e)
        rows.append(row)
        print("SEC", json.dumps(row), flush=True)
        time.sleep(0.25)

    active = [r for r in rows if r["statusClass"].startswith("ACTIVE")]
    delisted = [r for r in rows if r["statusClass"].startswith("DELISTED")]
    summary = {
        "year": 2006,
        "purpose": "Structural pilot for conservative issuer-country hierarchy: mapped ticker first; direct exact issuer query if one historical CIK; otherwise issuer-search candidate CIKs are queried and accepted only if exactly one has filings no later than 2006-12-31. State/country comes from historical SEC filing/browse metadata. No returns or universe rank used.",
        "sampleCount": len(rows),
        "resolvedCikCount": sum(1 for r in rows if r.get("resolvedCik")),
        "resolvedStateCount": sum(1 for r in rows if r.get("resolvedStateCode")),
        "activeResolvedRate": sum(1 for r in active if r.get("resolvedStateCode")) / max(1, len(active)),
        "delistedResolvedRate": sum(1 for r in delisted if r.get("resolvedStateCode")) / max(1, len(delisted)),
        "resolutionSources": {k: sum(1 for r in rows if r.get("resolutionSource") == k) for k in ["TICKER","ISSUER_DIRECT_SINGLE_CIK","ISSUER_CANDIDATE_SINGLE_PIT_CIK"]},
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
