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
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "text/plain,text/html,*/*"}

ISSUERS = [
    {"name": "Exxon Mobil Corp", "expectedClass": "US"},
    {"name": "Microsoft Corp", "expectedClass": "US"},
    {"name": "SAP AG", "expectedClass": "FOREIGN"},
    {"name": "BP PLC", "expectedClass": "FOREIGN"},
    {"name": "HSBC Holdings PLC", "expectedClass": "FOREIGN"},
]

CIK_LABEL_RE = re.compile(r"(?:CIK|Central Index Key)\D{0,30}(\d{6,10})", re.I)
CIK_TITLE_RE = re.compile(r"Title:\s*[^\r\n]*\((\d{10})\)", re.I)
ACCESSION_RE = re.compile(r"\b(\d{10}-\d{2}-\d{6})\b")
ARCHIVE_RE = re.compile(r"https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"'<>\)]+", re.I)
RAW_STATE_RE = re.compile(r"<STATE-OF-INCORPORATION>\s*([^\r\n<]+)", re.I)
RENDERED_STATE_RE = re.compile(r"State\s+of\s+Inc(?:orp)?\.?:\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?\b", re.I)
US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
}


def get(url: str, timeout: int = 12) -> tuple[str, str, int]:
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


def ciks_from(text: str) -> list[str]:
    vals = set(CIK_LABEL_RE.findall(text)) | set(CIK_TITLE_RE.findall(text))
    return sorted(x.zfill(10) for x in vals)


def state_codes(text: str) -> list[str]:
    vals = [x.strip().upper() for x in RAW_STATE_RE.findall(text)]
    vals += [x.strip().upper() for x in RENDERED_STATE_RE.findall(text)]
    return list(dict.fromkeys(vals))


def sec_query(params: dict[str, str]) -> str:
    return "https://www.sec.gov/cgi-bin/browse-edgar?" + urllib.parse.urlencode(params)


def search_company(name: str) -> dict:
    url = sec_query({
        "action": "getcompany",
        "company": name,
        "type": "",
        "dateb": "20061231",
        "owner": "exclude",
        "count": "40",
    })
    text, transport, nbytes = get(url)
    return {
        "queryUrl": url,
        "transport": transport,
        "bytes": nbytes,
        "ciks": ciks_from(text)[:10],
        "stateCodesInLookup": state_codes(text),
        "accessions": ACCESSION_RE.findall(text)[:20],
        "archiveUrls": list(dict.fromkeys(ARCHIVE_RE.findall(text)))[:20],
        "snippet": clean_text(text)[:1200],
    }


def filings_by_cik(cik: str) -> dict:
    url = sec_query({
        "action": "getcompany",
        "CIK": cik,
        "type": "",
        "dateb": "20061231",
        "owner": "exclude",
        "count": "40",
    })
    text, transport, nbytes = get(url)
    return {
        "queryUrl": url,
        "transport": transport,
        "bytes": nbytes,
        "stateCodesInLookup": state_codes(text),
        "accessions": ACCESSION_RE.findall(text)[:20],
        "archiveUrls": list(dict.fromkeys(ARCHIVE_RE.findall(text)))[:20],
        "snippet": clean_text(text)[:1200],
    }


def inspect_filing_index(url: str) -> dict:
    text, transport, nbytes = get(url)
    codes = state_codes(text)
    return {
        "url": url,
        "transport": transport,
        "bytes": nbytes,
        "stateCodes": codes,
        "usByStateCode": bool(codes) and all(c in US_CODES for c in codes),
        "snippet": clean_text(text)[:1000],
    }


def main() -> None:
    results = []
    for item in ISSUERS:
        row = {**item}
        try:
            lookup = search_company(item["name"])
            row["companyLookup"] = lookup
            if lookup["ciks"]:
                filings = filings_by_cik(lookup["ciks"][0])
                row["filingLookup"] = filings
                attempts = []
                for url in filings.get("archiveUrls", [])[:3]:
                    try:
                        attempts.append(inspect_filing_index(url))
                    except Exception as e:
                        attempts.append({"url": url, "error": repr(e)})
                    time.sleep(0.25)
                row["filingIndexAttempts"] = attempts
                codes = [c for a in attempts for c in a.get("stateCodes", [])]
                if not codes:
                    codes = filings.get("stateCodesInLookup", [])
                if codes:
                    row["resolvedStateCode"] = codes[0]
                    row["resolvedClass"] = "US" if codes[0] in US_CODES else "FOREIGN_OR_NONSTATE"
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
        print("ISSUER", json.dumps(row, ensure_ascii=False), flush=True)
        time.sleep(0.5)

    summary = {
        "year": 2006,
        "purpose": "Transport/structure pilot only: test whether issuer name -> SEC CIK -> filing dated no later than 2006-12-31 -> state-of-incorporation can provide a point-in-time issuer-organization-country signal. Fixed US/foreign examples; no returns or universe outcomes used.",
        "issuerCount": len(results),
        "lookupWithCik": sum(1 for r in results if r.get("companyLookup", {}).get("ciks")),
        "withArchiveUrl": sum(1 for r in results if r.get("filingLookup", {}).get("archiveUrls")),
        "withHistoricalStateCode": sum(1 for r in results if r.get("resolvedStateCode")),
        "classificationCorrect": sum(1 for r in results if (r.get("resolvedClass") == r.get("expectedClass") or (r.get("expectedClass") == "FOREIGN" and r.get("resolvedClass") == "FOREIGN_OR_NONSTATE"))),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
