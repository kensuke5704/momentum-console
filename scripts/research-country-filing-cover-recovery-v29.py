#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
SHARD = int(os.environ.get("SHARD_INDEX", "0"))
SRC = R / f"country-index-headers-recovery-v29-shard-{SHARD}.json"
OUT = R / f"country-filing-cover-recovery-v29-shard-{SHARD}.json"

UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "text/plain,text/html,*/*",
    "Accept-Encoding": "identity",
}

US_STATE_NAMES = {
    "ALABAMA","ALASKA","ARIZONA","ARKANSAS","CALIFORNIA","COLORADO","CONNECTICUT","DELAWARE",
    "FLORIDA","GEORGIA","HAWAII","IDAHO","ILLINOIS","INDIANA","IOWA","KANSAS","KENTUCKY",
    "LOUISIANA","MAINE","MARYLAND","MASSACHUSETTS","MICHIGAN","MINNESOTA","MISSISSIPPI","MISSOURI",
    "MONTANA","NEBRASKA","NEVADA","NEW HAMPSHIRE","NEW JERSEY","NEW MEXICO","NEW YORK",
    "NORTH CAROLINA","NORTH DAKOTA","OHIO","OKLAHOMA","OREGON","PENNSYLVANIA","RHODE ISLAND",
    "SOUTH CAROLINA","SOUTH DAKOTA","TENNESSEE","TEXAS","UTAH","VERMONT","VIRGINIA","WASHINGTON",
    "WEST VIRGINIA","WISCONSIN","WYOMING","DISTRICT OF COLUMBIA",
}
US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA",
    "ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR",
    "PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
}
FORM_PRIORITY = {"10-K": 0, "10-K/A": 1, "10-Q": 2, "10-Q/A": 3, "8-K": 4, "8-K/A": 5}

INDEX_CACHE: dict[str, tuple[str,str]] = {}
DOC_CACHE: dict[str, tuple[str,str]] = {}


def normalize_company(s: str) -> str:
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"\s*/[A-Z0-9]{2,3}/?\s*$", "", s)
    s = re.sub(r"\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return " ".join(s.split())


def fetch_jina(url: str, limit: int = 1_000_000, timeout: int = 25) -> tuple[str,str]:
    candidate = "https://r.jina.ai/" + url
    req = urllib.request.Request(candidate, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit).decode("utf-8", "replace"), candidate


def accession_parts(filename: str):
    m = re.search(r"edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$", filename or "", re.I)
    if not m:
        return None
    cik_dir = str(int(m.group(1)))
    acc = m.group(2)
    return cik_dir, acc, acc.replace("-", "")


def filing_index_url(filename: str) -> str | None:
    p = accession_parts(filename)
    if not p:
        return None
    cik_dir, acc, acc_no = p
    return f"https://www.sec.gov/Archives/edgar/data/{cik_dir}/{acc_no}/{acc}-index.htm"


def fetch_index(filename: str) -> tuple[str,str]:
    if filename in INDEX_CACHE:
        return INDEX_CACHE[filename]
    url = filing_index_url(filename)
    if not url:
        raise RuntimeError("NO_INDEX_URL")
    out = fetch_jina(url, 800_000, 25)
    INDEX_CACHE[filename] = out
    return out


def document_links(index_text: str, filename: str) -> list[str]:
    p = accession_parts(filename)
    if not p:
        return []
    cik_dir, _acc, acc_no = p
    prefix = f"https://www.sec.gov/Archives/edgar/data/{cik_dir}/{acc_no}/"
    links = []
    # Jina normally renders SEC document-table links as Markdown absolute links.
    for u in re.findall(r"https://www\.sec\.gov/Archives/edgar/data/\d+/\d+/[^\s\)\]\"'<>]+", index_text, re.I):
        u = html.unescape(u).rstrip(".,;:")
        if not u.startswith(prefix):
            continue
        low = u.lower()
        if low.endswith(("-index.htm", "-index.html", "-index-headers.html", ".txt")):
            continue
        if re.search(r"\.(?:htm|html)$", low) and u not in links:
            links.append(u)
    # Some Jina pages keep relative SEC links.
    for rel in re.findall(r"\]\(([^\)]+\.(?:htm|html))\)", index_text, re.I):
        rel = html.unescape(rel)
        if rel.startswith("http"):
            u = rel
        else:
            u = prefix + rel.lstrip("/")
        if u.startswith(prefix) and u not in links and "-index." not in u.lower():
            links.append(u)
    return links[:12]


def fetch_doc(url: str) -> tuple[str,str]:
    if url in DOC_CACHE:
        return DOC_CACHE[url]
    out = fetch_jina(url, 1_500_000, 30)
    DOC_CACHE[url] = out
    return out


def issuer_present(text: str, issuer_variants: list[str]) -> bool:
    nt = normalize_company(text[:180_000])
    # Avoid requiring exact punctuation/legal suffix; the CIK+accession already binds the filing.
    for issuer in issuer_variants:
        q = normalize_company(issuer)
        if len(q) >= 5 and q in nt:
            return True
    return False


def jurisdiction_from_cover(text: str) -> tuple[str | None, str | None]:
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("\r", "")
    phrase_re = re.compile(r"state\s+or\s+other\s+jurisdiction\s+of\s+incorporation\s+or\s+organization", re.I)
    for m in phrase_re.finditer(plain[:250_000]):
        before = plain[max(0, m.start()-700):m.start()]
        # Jina table rendering places the jurisdiction value before the label.
        lines = [" ".join(x.split()) for x in before.splitlines() if x.strip()]
        candidates = []
        for line in lines[-12:]:
            # Split Markdown table cells; prefer short cells.
            for cell in re.split(r"\s*\|\s*", line):
                cell = re.sub(r"[*_`]+", "", cell).strip(" .,:;()[]")
                if 2 <= len(cell) <= 40:
                    candidates.append(cell.upper())
        for c in reversed(candidates):
            if c in US_CODES or c in US_STATE_NAMES:
                return c, "US"
            # Foreign jurisdiction names are accepted only when clearly textual and not generic cover labels/numbers.
            if re.fullmatch(r"[A-Z][A-Z .&'-]{2,39}", c) and c not in {
                "UNITED STATES","SECURITIES AND EXCHANGE COMMISSION","WASHINGTON D C","FORM","YES","NO",
            }:
                if not re.search(r"(?:COMMISSION|REPORT|EMPLOYER|IDENTIFICATION|ADDRESS|REGISTRANT|NUMBER|EXCHANGE|CLASS)$", c):
                    return c, "NON_US"
        # Also handle common inline constructions.
        mm = re.search(r"([A-Za-z][A-Za-z .&'-]{1,35})\s*(?:\||\n)\s*\(?State\s+or\s+other\s+jurisdiction", before[-300:] + plain[m.start():m.end()+20], re.I)
        if mm:
            c = " ".join(mm.group(1).upper().split()).strip(" .,:;()")
            if c in US_CODES or c in US_STATE_NAMES:
                return c, "US"
    return None, None


def resolve_row(row: dict) -> dict:
    cik = str(row.get("historicalExactCik") or "").zfill(10)
    issuers = list(row.get("matchedIssuerForms") or row.get("issuerVariants") or [])
    report_date = row.get("asOfReportDate")
    attempts = []
    candidates = []
    for a in row.get("attempts") or []:
        form = str(a.get("form") or "").upper()
        date = a.get("dateFiled")
        fn = a.get("filename")
        if form not in FORM_PRIORITY or not fn or not date or (report_date and date > report_date):
            continue
        candidates.append((FORM_PRIORITY[form], -int(date.replace("-", "")), fn, form, date))
    candidates.sort()
    seen = set()
    out = {
        "ticker": row.get("ticker"), "securityId": row.get("securityId"), "asOfReportDate": report_date,
        "issuerVariants": row.get("issuerVariants") or [], "matchedIssuerForms": issuers,
        "historicalExactCik": cik if cik.strip("0") else None, "classification": "UNKNOWN", "attempts": attempts,
    }
    if not cik.strip("0"):
        return out
    for _prio, _negdate, fn, form, date in candidates[:6]:
        if fn in seen:
            continue
        seen.add(fn)
        one = {"form": form, "dateFiled": date, "filename": fn, "indexUrl": filing_index_url(fn)}
        try:
            idx, idx_transport = fetch_index(fn)
            links = document_links(idx, fn)
            one["indexTransport"] = idx_transport
            one["documentLinkCount"] = len(links)
            for url in links[:6]:
                da = {"documentUrl": url}
                try:
                    text, tr = fetch_doc(url)
                    da["transport"] = tr
                    da["issuerPresent"] = issuer_present(text, issuers)
                    juris, cls = jurisdiction_from_cover(text)
                    da["jurisdiction"] = juris
                    if cls and da["issuerPresent"]:
                        da["classification"] = cls
                        one.setdefault("documentAttempts", []).append(da)
                        out.update({
                            "classification": cls,
                            "jurisdiction": juris,
                            "resolutionSource": "PIT_FILING_PRIMARY_DOCUMENT_COVER_JURISDICTION",
                            "evidenceForm": form,
                            "evidenceDateFiled": date,
                            "evidenceFilename": fn,
                            "evidenceDocumentUrl": url,
                            "evidenceTransport": tr,
                        })
                        attempts.append(one)
                        return out
                except Exception as e:
                    da["error"] = type(e).__name__
                one.setdefault("documentAttempts", []).append(da)
        except Exception as e:
            one["error"] = type(e).__name__
        attempts.append(one)
        time.sleep(0.01)
    return out


def main() -> None:
    data = json.loads(SRC.read_text())
    rows = data.get("results") or []
    results = []
    counts = {"US": 0, "NON_US": 0, "UNKNOWN": 0}
    for i, row in enumerate(rows, 1):
        r = resolve_row(row)
        results.append(r)
        counts[r["classification"]] += 1
        if i % 25 == 0:
            print("PROGRESS", json.dumps({"shard": SHARD, "done": i, "counts": counts, "indexCache": len(INDEX_CACHE), "docCache": len(DOC_CACHE)}), flush=True)
    out = {
        "purpose": (
            "Return-independent PIT recovery of strict-country UNKNOWN identities from historical SEC filing primary-document cover pages. "
            "The historical exact issuer-form -> unique CIK seed and pre-report-date filing candidates are inherited from the accepted strict resolver. "
            "A classification is promoted only when a document inside that exact historical accession contains the issuer and the cover label "
            "'State or other jurisdiction of incorporation or organization' with an explicit jurisdiction. No current ticker metadata, current country/state, "
            "fuzzy identity matching, US default, ranks, returns or strategy outcomes are used."
        ),
        "shardIndex": SHARD,
        "inputCount": len(rows),
        "classificationCounts": counts,
        "resolvedCount": counts["US"] + counts["NON_US"],
        "indexFetchCount": len(INDEX_CACHE),
        "documentFetchCount": len(DOC_CACHE),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k:v for k,v in out.items() if k != "results"}), flush=True)

if __name__ == "__main__":
    main()
