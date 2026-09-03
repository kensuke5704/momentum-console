#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "data/research/nq-npx-mapping-2006.json"
OUT = ROOT / "data/research/sec-us-attribution-sample-2006.json"
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "text/plain,text/html,*/*"}
SAMPLE_N = 24

ARCHIVE_CIK_RE = re.compile(r"/Archives/edgar/data/(\d+)/", re.I)
ARCHIVE_RE = re.compile(r"https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"'<>\)]+", re.I)
STATE_RE = re.compile(r"State\s+of\s+Inc(?:orp)?\.?:\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?\b", re.I)
CANDIDATE_ROW_RE = re.compile(r"\|\s*\[(\d{10})\]\([^\)]*CIK=\1[^\)]*\)\s*\|\s*([^|]+?)\s*\|", re.I)
US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"
}


def get(url: str, timeout: int = 9) -> tuple[str, str]:
    last = None
    for candidate in ("https://r.jina.ai/" + url, url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(2_000_000).decode("utf-8", "replace"), candidate
        except Exception as e:
            last = repr(e)
    raise RuntimeError(last or "fetch failed")


def sec_url(params: dict[str, str]) -> str:
    return "https://www.sec.gov/cgi-bin/browse-edgar?" + urllib.parse.urlencode(params)


def clean_issuer(s: str) -> str:
    s = re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", s, flags=re.I)
    return " ".join(s.replace("’", "'").split()).strip(" .,-")


def normalize_name(s: str) -> str:
    s = clean_issuer(s).upper().replace("&", " AND ")
    s = re.sub(r"\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return " ".join(s.split())


def issuer_query_variants(issuer: str) -> list[str]:
    clean = clean_issuer(issuer)
    simple = re.sub(r"[^A-Za-z0-9& ]+", " ", clean)
    simple = " ".join(simple.split())
    no_suffix = re.sub(r"\b(?:Incorporated|Inc|Corporation|Corp|Company|Co|Limited|Ltd|PLC|AG)\b\.?", " ", simple, flags=re.I)
    no_suffix = " ".join(no_suffix.split())
    no_the = re.sub(r"^The\s+", "", no_suffix, flags=re.I)
    out = []
    for q in (clean, simple, no_suffix, no_the):
        q = q.strip(" .,-")
        if len(q) >= 3 and q not in out:
            out.append(q)
    return out


def parse_browse(url: str) -> dict:
    text, transport = get(url)
    urls = list(dict.fromkeys(ARCHIVE_RE.findall(text)))
    ciks = list(dict.fromkeys(m.group(1).zfill(10) for u in urls for m in [ARCHIVE_CIK_RE.search(u)] if m))
    candidates = []
    for cik, raw_name in CANDIDATE_ROW_RE.findall(text):
        name = re.sub(r"\s+SIC:.*$", "", raw_name.strip(), flags=re.I)
        candidates.append({"cik": cik, "name": name, "normalizedName": normalize_name(name)})
    return {"transport": transport, "archiveUrls": urls[:16], "ciksFromArchive": ciks, "companyCandidates": candidates[:30]}


def browse_ticker(ticker: str, dateb: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","CIK":ticker,"type":"","dateb":dateb.replace("-", ""),"owner":"exclude","count":"40"}))


def browse_issuer(issuer: str, dateb: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","company":issuer,"type":"","dateb":dateb.replace("-", ""),"owner":"exclude","count":"40"}))


def browse_cik(cik: str, dateb: str) -> dict:
    return parse_browse(sec_url({"action":"getcompany","CIK":cik,"type":"","dateb":dateb.replace("-", ""),"owner":"exclude","count":"40"}))


def state_from_archives(urls: list[str]) -> tuple[str | None, int, list[str]]:
    errors = []
    attempts = 0
    for url in urls[:12]:
        attempts += 1
        try:
            text, _ = get(url)
            states = list(dict.fromkeys(x.upper() for x in STATE_RE.findall(text)))
            if states:
                return states[0], attempts, errors
        except Exception as e:
            errors.append(type(e).__name__)
        time.sleep(0.10)
    return None, attempts, errors


def resolve_issuer_variants(issuer: str, dateb: str) -> tuple[dict | None, list[dict]]:
    target = normalize_name(issuer)
    audits = []
    direct_by_cik: dict[str, dict] = {}
    candidate_names: dict[str, dict] = {}
    for query in issuer_query_variants(issuer):
        try:
            b = browse_issuer(query, dateb)
            audits.append({"query": query, "archiveCount": len(b.get("archiveUrls", [])), "ciks": b.get("ciksFromArchive", []), "candidateCount": len(b.get("companyCandidates", []))})
            if b.get("archiveUrls") and len(b.get("ciksFromArchive", [])) == 1:
                direct_by_cik[b["ciksFromArchive"][0]] = b
            for c in b.get("companyCandidates", []):
                candidate_names[c["cik"]] = c
        except Exception as e:
            audits.append({"query": query, "error": type(e).__name__})
        time.sleep(0.08)
    if len(direct_by_cik) == 1:
        cik, b = next(iter(direct_by_cik.items()))
        return {"source": "ISSUER_VARIANT_DIRECT_SINGLE_PIT_CIK", "cik": cik, "browse": b}, audits
    exact = [c for c in candidate_names.values() if c["normalizedName"] == target]
    pool = exact if exact else list(candidate_names.values())
    viable = []
    for c in pool[:10]:
        try:
            b = browse_cik(c["cik"], dateb)
            audits.append({"candidateCik": c["cik"], "candidateName": c["name"], "candidateArchiveCount": len(b.get("archiveUrls", []))})
            if b.get("archiveUrls"):
                viable.append((c, b))
        except Exception as e:
            audits.append({"candidateCik": c["cik"], "candidateName": c["name"], "error": type(e).__name__})
        time.sleep(0.08)
    if len(viable) == 1:
        c, b = viable[0]
        return {"source": "ISSUER_VARIANT_CANDIDATE_SINGLE_PIT_CIK", "cik": c["cik"], "browse": b, "candidate": c}, audits
    return None, audits


def resolve_security(row: dict) -> dict:
    ticker, issuer, dateb = row["ticker"], row["issuer"], row["asOfReportDate"]
    out = {**row}
    try:
        b = browse_ticker(ticker, dateb)
        source = "TICKER"
        if not b.get("archiveUrls"):
            resolved, audits = resolve_issuer_variants(issuer, dateb)
            out["issuerAudits"] = audits
            if resolved:
                source = resolved["source"]
                b = resolved["browse"]
                if resolved.get("candidate"):
                    out["candidate"] = resolved["candidate"]
        out["archiveCount"] = len(b.get("archiveUrls", []))
        out["ciks"] = b.get("ciksFromArchive", [])
        state, attempts, errors = state_from_archives(b.get("archiveUrls", []))
        out["filingAttempts"] = attempts
        if errors:
            out["transportErrors"] = errors
        if state:
            out["stateCode"] = state
            out["classification"] = "US" if state in US_CODES else "NON_US"
            out["resolutionSource"] = source
        else:
            out["classification"] = "UNKNOWN"
    except Exception as e:
        out["classification"] = "UNKNOWN"
        out["error"] = repr(e)
    return out


def main() -> None:
    mapping = json.loads(MAPPING.read_text())
    identities = {}
    for d in mapping.get("details", []):
        if d.get("status") != "MATCHED_UNIQUE" or len(d.get("identities", [])) != 1:
            continue
        ident = d["identities"][0]
        key = (ident["ticker"], ident["securityId"])
        existing = identities.get(key)
        candidate = {"ticker": ident["ticker"], "securityId": ident["securityId"], "issuer": d["description"], "asOfReportDate": d["reportDate"]}
        if existing is None or candidate["asOfReportDate"] < existing["asOfReportDate"]:
            identities[key] = candidate
    population = sorted(identities.values(), key=lambda x: (x["ticker"], x["securityId"], x["issuer"]))
    if not population:
        raise RuntimeError("No unique mapped identities found")
    n = min(SAMPLE_N, len(population))
    positions = sorted(set(min(len(population) - 1, (i * len(population)) // n) for i in range(n)))
    sample = [population[i] for i in positions]
    print("SAMPLE", json.dumps({"uniqueIdentityPopulation": len(population), "sampleN": len(sample), "positions": positions}), flush=True)

    results = []
    for i, row in enumerate(sample, 1):
        resolved = resolve_security(row)
        results.append(resolved)
        print(f"{i}/{len(sample)}", json.dumps(resolved), flush=True)
        time.sleep(0.15)

    counts = {k: sum(1 for r in results if r["classification"] == k) for k in ["US", "NON_US", "UNKNOWN"]}
    sources = ["TICKER","ISSUER_VARIANT_DIRECT_SINGLE_PIT_CIK","ISSUER_VARIANT_CANDIDATE_SINGLE_PIT_CIK"]
    summary = {
        "year": 2006,
        "purpose": "Deterministic structural coverage test of the candidate legacy US attribution hierarchy on actual EC-filtered uniquely N-PX-mapped securities. No returns, universe ranks, or strategy outcomes used.",
        "populationRule": "Deduplicate MATCHED_UNIQUE identities by ticker+securityId; use earliest N-Q report date per identity so no later filing state is required.",
        "sampleRule": f"{SAMPLE_N} equal-quantile positions after deterministic ticker,securityId,issuer sort. Same frozen positions as prior run.",
        "hierarchy": "SEC ticker query by earliest report date; if absent, deterministic structural issuer query variants (footnote/punctuation/legal-suffix cleanup) are tried. A direct issuer result is accepted only if it resolves to one historical CIK; candidate-table results are accepted only when exactly one candidate has filings by that report date. State/country must be found on a historical filing page; otherwise UNKNOWN.",
        "uniqueIdentityPopulation": len(population),
        "sampleCount": len(results),
        "classificationCounts": counts,
        "resolvedRate": (counts["US"] + counts["NON_US"]) / len(results),
        "usRateAmongResolved": counts["US"] / max(1, counts["US"] + counts["NON_US"]),
        "resolutionSources": {s: sum(1 for r in results if r.get("resolutionSource") == s) for s in sources},
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
