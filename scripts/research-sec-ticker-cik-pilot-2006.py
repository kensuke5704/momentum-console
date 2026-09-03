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
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
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


def browse_by_ticker(ticker: str) -> dict:
    url = "https://www.sec.gov/cgi-bin/browse-edgar?" + urllib.parse.urlencode({
        "action": "getcompany",
        "CIK": ticker,
        "type": "",
        "dateb": "20061231",
        "owner": "exclude",
        "count": "40",
    })
    text, transport, nbytes = get(url)
    urls = list(dict.fromkeys(ARCHIVE_RE.findall(text)))
    ciks = list(dict.fromkeys(m.group(1).zfill(10) for u in urls for m in [ARCHIVE_CIK_RE.search(u)] if m))
    states = list(dict.fromkeys(x.upper() for x in STATE_RE.findall(text)))
    return {"url": url, "transport": transport, "bytes": nbytes, "archiveUrls": urls[:10], "ciksFromArchive": ciks, "stateCodesOnBrowse": states, "snippet": " ".join(text.split())[:900]}


def inspect_index(url: str) -> dict:
    text, transport, nbytes = get(url)
    states = list(dict.fromkeys(x.upper() for x in STATE_RE.findall(text)))
    return {"url": url, "transport": transport, "bytes": nbytes, "stateCodes": states, "snippet": " ".join(text.split())[:700]}


def main() -> None:
    rows = []
    for item in SAMPLE:
        row = {**item}
        try:
            browse = browse_by_ticker(item["ticker"])
            row["browse"] = browse
            if browse["archiveUrls"]:
                idx = inspect_index(browse["archiveUrls"][0])
                row["firstHistoricalFiling"] = idx
                codes = idx["stateCodes"] or browse["stateCodesOnBrowse"]
                if codes:
                    row["resolvedStateCode"] = codes[0]
                    row["resolvedUS"] = codes[0] in US_CODES
        except Exception as e:
            row["error"] = repr(e)
        rows.append(row)
        print("TICKER", json.dumps(row), flush=True)
        time.sleep(0.4)

    summary = {
        "year": 2006,
        "purpose": "Structural transport pilot: test SEC browse-edgar ticker -> historical filing -> CIK/state-of-incorporation for a fixed mix of active and delisted 2006-era securities. No returns or universe rank used.",
        "sampleCount": len(rows),
        "withHistoricalArchive": sum(1 for r in rows if r.get("browse", {}).get("archiveUrls")),
        "withCikFromArchive": sum(1 for r in rows if r.get("browse", {}).get("ciksFromArchive")),
        "withStateCode": sum(1 for r in rows if r.get("resolvedStateCode")),
        "activeArchiveRate": sum(1 for r in rows if r["statusClass"].startswith("ACTIVE") and r.get("browse", {}).get("archiveUrls")) / max(1, sum(1 for r in rows if r["statusClass"].startswith("ACTIVE"))),
        "delistedArchiveRate": sum(1 for r in rows if r["statusClass"].startswith("DELISTED") and r.get("browse", {}).get("archiveUrls")) / max(1, sum(1 for r in rows if r["statusClass"].startswith("DELISTED"))),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
