#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "research" / "sec-issuer-country-pilot-2006.json"
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "text/plain,text/html,application/atom+xml,*/*"}

ISSUERS = [
    {"name": "Exxon Mobil Corp", "expectedClass": "US"},
    {"name": "Microsoft Corp", "expectedClass": "US"},
    {"name": "SAP AG", "expectedClass": "FOREIGN"},
    {"name": "BP PLC", "expectedClass": "FOREIGN"},
    {"name": "HSBC Holdings PLC", "expectedClass": "FOREIGN"},
]

STATE_RE = re.compile(r"<STATE-OF-INCORPORATION>\s*([^\r\n<]+)", re.I)
CIK_RE = re.compile(r"(?:CIK|Central Index Key)\D{0,20}(\d{6,10})", re.I)
ACCESSION_RE = re.compile(r"\b(\d{10}-\d{2}-\d{6})\b")
ARCHIVE_RE = re.compile(r"https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"'<>]+", re.I)


def get(url: str, timeout: int = 30) -> tuple[str, str, int]:
    last = None
    for candidate in (url, "https://r.jina.ai/" + url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(3_000_000)
            return raw.decode("utf-8", "replace"), candidate, len(raw)
        except Exception as e:
            last = repr(e)
    raise RuntimeError(last or "fetch failed")


def clean_text(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    return " ".join(s.split())


def search_company(name: str) -> dict:
    q = urllib.parse.urlencode({
        "action": "getcompany",
        "company": name,
        "type": "",
        "dateb": "20061231",
        "owner": "exclude",
        "count": "40",
        "output": "atom",
    })
    url = "https://www.sec.gov/cgi-bin/browse-edgar?" + q
    text, transport, nbytes = get(url)
    ciks = sorted(set(CIK_RE.findall(text)))
    accessions = ACCESSION_RE.findall(text)
    archive_urls = ARCHIVE_RE.findall(text)
    return {
        "queryUrl": url,
        "transport": transport,
        "bytes": nbytes,
        "ciks": ciks[:10],
        "accessions": accessions[:20],
        "archiveUrls": archive_urls[:20],
        "snippet": clean_text(text)[:1200],
    }


def fetch_submission_header(cik: str) -> dict:
    # Historical complete-submission listing. If company browse resolves CIK, query filings
    # near 2006 and inspect the complete submission text for SGML STATE-OF-INCORPORATION.
    q = urllib.parse.urlencode({
        "action": "getcompany",
        "CIK": cik,
        "type": "10-K|20-F|40-F",
        "dateb": "20061231",
        "owner": "exclude",
        "count": "40",
    })
    url = "https://www.sec.gov/cgi-bin/browse-edgar?" + q
    text, transport, nbytes = get(url)
    accs = ACCESSION_RE.findall(text)
    urls = ARCHIVE_RE.findall(text)
    return {"queryUrl": url, "transport": transport, "bytes": nbytes, "accessions": accs[:20], "archiveUrls": urls[:20], "snippet": clean_text(text)[:1200]}


def try_archive_url(url: str) -> dict:
    text, transport, nbytes = get(url)
    states = [x.strip() for x in STATE_RE.findall(text)]
    return {"url": url, "transport": transport, "bytes": nbytes, "stateOfIncorporation": states[:10], "snippet": clean_text(text)[:1000]}


def main() -> None:
    results = []
    for item in ISSUERS:
        row = {**item}
        try:
            lookup = search_company(item["name"])
            row["companyLookup"] = lookup
            if lookup["ciks"]:
                filings = fetch_submission_header(lookup["ciks"][0])
                row["filingLookup"] = filings
                archive_attempts = []
                for url in filings.get("archiveUrls", [])[:3]:
                    try:
                        archive_attempts.append(try_archive_url(url))
                    except Exception as e:
                        archive_attempts.append({"url": url, "error": repr(e)})
                    time.sleep(0.5)
                row["archiveAttempts"] = archive_attempts
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
        print("ISSUER", json.dumps(row, ensure_ascii=False), flush=True)
        time.sleep(1.0)

    summary = {
        "year": 2006,
        "purpose": "Transport/structure pilot only: test whether historical SEC company lookup and filing SGML can provide issuer organization jurisdiction for a fixed mix of US and foreign issuers. No returns or universe outcomes used.",
        "issuerCount": len(results),
        "lookupWithCik": sum(1 for r in results if r.get("companyLookup", {}).get("ciks")),
        "withArchiveUrl": sum(1 for r in results if r.get("filingLookup", {}).get("archiveUrls")),
        "withStateOfIncorporation": sum(1 for r in results if any(a.get("stateOfIncorporation") for a in r.get("archiveAttempts", []))),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
