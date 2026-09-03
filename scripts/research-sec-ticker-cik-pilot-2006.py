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


def parse_browse(url: str) -> dict:
    text, transport, nbytes = get(url)
    urls = list(dict.fromkeys(ARCHIVE_RE.findall(text)))
    ciks = list(dict.fromkeys(m.group(1).zfill(10) for u in urls for m in [ARCHIVE_CIK_RE.search(u)] if m))
    states = list(dict.fromkeys(x.upper() for x in STATE_RE.findall(text)))
    return {"url": url, "transport": transport, "bytes": nbytes, "archiveUrls": urls[:12], "ciksFromArchive": ciks, "stateCodesOnBrowse": states, "snippet": " ".join(text.split())[:1000]}


def browse_by_ticker(ticker: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","CIK":ticker,"type":"","dateb":"20061231","owner":"exclude","count":"40"}))


def browse_by_issuer(issuer: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","company":issuer,"type":"","dateb":"20061231","owner":"exclude","count":"40"}))


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
        time.sleep(0.2)
    if browse.get("stateCodesOnBrowse"):
        return browse["stateCodesOnBrowse"][0], attempts
    return None, attempts


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
                # Accept issuer fallback only when historical archive URLs resolve to one unique CIK.
                if issuer_browse.get("archiveUrls") and len(issuer_browse.get("ciksFromArchive", [])) == 1:
                    source = "ISSUER_EXACT_QUERY_SINGLE_CIK"
                    browse = issuer_browse
            state, attempts = resolve_from_browse(browse)
            row["historicalFilingAttempts"] = attempts
            if browse.get("archiveUrls") and browse.get("ciksFromArchive"):
                row["resolvedCik"] = browse["ciksFromArchive"][0] if len(browse["ciksFromArchive"]) == 1 else None
            if state:
                row["resolvedStateCode"] = state
                row["resolvedUS"] = state in US_CODES
                row["resolutionSource"] = source
        except Exception as e:
            row["error"] = repr(e)
        rows.append(row)
        print("SEC", json.dumps(row), flush=True)
        time.sleep(0.35)

    active = [r for r in rows if r["statusClass"].startswith("ACTIVE")]
    delisted = [r for r in rows if r["statusClass"].startswith("DELISTED")]
    summary = {
        "year": 2006,
        "purpose": "Structural pilot for a conservative issuer-country hierarchy: mapped ticker -> SEC historical filing; if ticker fails, exact issuer-name SEC query is accepted only when historical archives resolve to one unique CIK. State/country is read from filings no later than 2006-12-31. No returns or universe rank used.",
        "sampleCount": len(rows),
        "resolvedCikCount": sum(1 for r in rows if r.get("resolvedCik")),
        "resolvedStateCount": sum(1 for r in rows if r.get("resolvedStateCode")),
        "activeResolvedRate": sum(1 for r in active if r.get("resolvedStateCode")) / max(1, len(active)),
        "delistedResolvedRate": sum(1 for r in delisted if r.get("resolvedStateCode")) / max(1, len(delisted)),
        "tickerResolvedCount": sum(1 for r in rows if r.get("resolutionSource") == "TICKER"),
        "issuerFallbackResolvedCount": sum(1 for r in rows if r.get("resolutionSource") == "ISSUER_EXACT_QUERY_SINGLE_CIK"),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
