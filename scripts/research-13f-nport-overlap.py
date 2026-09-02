#!/usr/bin/env python3
"""Compare a free SEC Form 13F institutional-breadth proxy with the frozen N-PORT Top80.

Research only. Downloads SEC's official structured 13F ZIPs, uses filing dates for
point-in-time availability, applies the production N-PORT breadth score formula to
13F manager holdings, then maps issuer names to tickers using the repository's
N-PORT issuer names / company profiles. No production files are modified.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SEC_PAGE = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
UA = os.environ.get("SEC_USER_AGENT", "momentum-research/1.0 research@example.com")
START_YEAR = int(os.environ.get("OVERLAP_START_YEAR", "2020"))
END_YEAR = int(os.environ.get("OVERLAP_END_YEAR", "2026"))
TOP_N = int(os.environ.get("OVERLAP_TOP_N", "80"))
CACHE = ROOT / ".cache" / "sec-13f"
OUT = ROOT / "data" / "research" / "sec13f-nport-overlap.json"


def norm_name(s: str) -> str:
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"\b(CLASS|CL)\s+[A-Z0-9]+\b", " ", s)
    s = re.sub(r"\b(COMMON STOCK|COM STK|COMMON|ORDINARY SHARES?|ORD SHS?)\b", " ", s)
    s = re.sub(r"\b(INCORPORATED|INCORPORATION|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|HOLDINGS?|HLDGS?|GROUP)\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return " ".join(s.split())


def req(url: str) -> bytes:
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(r, timeout=90) as resp:
        return resp.read()


def sec_zip_links() -> list[tuple[str, str]]:
    html = req(SEC_PAGE).decode("utf-8", "replace")
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"]+_form13f\.zip)"[^>]*>(.*?)</a>', html, re.I | re.S):
        href, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        if href.startswith("/"):
            href = "https://www.sec.gov" + href
        years = [int(x) for x in re.findall(r"20\d{2}", href + " " + label)]
        if years and max(years) >= START_YEAR and min(years) <= END_YEAR:
            out.append((label.strip(), href))
    # de-duplicate while preserving page order
    seen = set(); dedup = []
    for x in out:
        if x[1] not in seen:
            seen.add(x[1]); dedup.append(x)
    return dedup


def load_aliases():
    names = defaultdict(set)
    boot = ROOT / "data" / "sec-nport" / "bootstrap.json.gz"
    if boot.exists():
        with gzip.open(boot, "rt", encoding="utf-8") as f:
            obj = json.load(f)
        snaps = obj.get("snapshots") or obj.get("filings") or []
        for filing in snaps:
            for h in filing.get("holdings", []):
                sym = str(h.get("symbol") or "").strip().upper()
                nm = norm_name(str(h.get("issuerName") or ""))
                if sym and nm:
                    names[nm].add(sym)
    prof = ROOT / "public" / "data" / "company-profiles.json"
    if prof.exists():
        obj = json.loads(prof.read_text())
        for sym, p in (obj.get("profiles") or {}).items():
            nm = norm_name(str(p.get("companyName") or ""))
            if nm:
                names[nm].add(sym.upper())
    unique = {n: next(iter(s)) for n, s in names.items() if len(s) == 1}
    ambiguous = {n: sorted(s) for n, s in names.items() if len(s) > 1}
    return unique, ambiguous


def open_tsv(z: zipfile.ZipFile, wanted: str):
    found = next((n for n in z.namelist() if n.upper().endswith(wanted.upper())), None)
    if not found:
        raise RuntimeError(f"{wanted} not found; files={z.namelist()[:20]}")
    return io.TextIOWrapper(z.open(found), encoding="utf-8-sig", errors="replace", newline="")


def pick(row: dict[str, str], *keys: str) -> str:
    upper = {k.upper(): v for k, v in row.items()}
    for k in keys:
        if k.upper() in upper:
            return upper[k.upper()] or ""
    return ""


@dataclass
class Filing:
    accession: str
    manager: str
    filing_date: str
    holdings: list[tuple[str, str, float]]  # cusip, issuer, value


def parse_zip(path: Path) -> list[Filing]:
    with zipfile.ZipFile(path) as z:
        with open_tsv(z, "SUBMISSION.tsv") as f:
            sr = csv.DictReader(f, delimiter="\t")
            meta = {}
            for r in sr:
                acc = pick(r, "ACCESSION_NUMBER", "ACCESSIONNUMBER")
                if not acc: continue
                cik = pick(r, "CIK", "FILINGMANAGER_CIK", "FILINGMANAGERCIK")
                fd = pick(r, "FILING_DATE", "FILINGDATE")[:10]
                form = pick(r, "SUBMISSIONTYPE", "FORM_TYPE", "FORMTYPE").upper()
                if form and "13F" not in form: continue
                meta[acc] = (cik or acc, fd)
        holdings = defaultdict(list)
        with open_tsv(z, "INFOTABLE.tsv") as f:
            ir = csv.DictReader(f, delimiter="\t")
            for r in ir:
                acc = pick(r, "ACCESSION_NUMBER", "ACCESSIONNUMBER")
                if acc not in meta: continue
                # Exclude options; production universe is long-equity breadth.
                if pick(r, "PUTCALL", "PUT_CALL").strip(): continue
                cusip = pick(r, "CUSIP").strip().upper()
                issuer = pick(r, "NAMEOFISSUER", "NAME_OF_ISSUER").strip()
                try: value = float(pick(r, "VALUE").replace(",", "") or 0)
                except ValueError: value = 0
                if cusip and issuer and value > 0:
                    holdings[acc].append((cusip, issuer, value))
    return [Filing(acc, meta[acc][0], meta[acc][1], hs) for acc, hs in holdings.items() if meta[acc][1]]


def month_end_dates() -> list[tuple[str, str]]:
    u = json.loads((ROOT / "data" / "universe-history.json").read_text())
    hist = u.get("history", [])
    out = []
    for x in hist:
        y = int(x["signalMonth"][:4])
        if START_YEAR <= y <= END_YEAR:
            out.append((x["signalMonth"], x["asOf"]))
    return out


def nport_by_month():
    u = json.loads((ROOT / "data" / "universe-history.json").read_text())
    return {x["signalMonth"]: [s["symbol"] for s in x.get("symbols", [])[:TOP_N]] for x in u.get("history", [])}


def build_13f_universe(filings: list[Filing], asof: str, aliases: dict[str, str]):
    latest = {}
    for f in filings:
        if f.filing_date <= asof:
            cur = latest.get(f.manager)
            if cur is None or (f.filing_date, f.accession) > (cur.filing_date, cur.accession):
                latest[f.manager] = f
    rows = defaultdict(lambda: {"managers": set(), "agg": 0.0, "max": 0.0, "rec": 0.0, "issuer": ""})
    asd = date.fromisoformat(asof)
    for f in latest.values():
        total = sum(v for _, _, v in f.holdings)
        if total <= 0: continue
        age = max(0, (asd - date.fromisoformat(f.filing_date)).days)
        rf = math.exp(-age / 120.0)
        # consolidate duplicate CUSIPs within manager before computing weight
        per = defaultdict(float); issuer_by = {}
        for cusip, issuer, value in f.holdings:
            per[cusip] += value; issuer_by[cusip] = issuer
        for cusip, value in per.items():
            w = 100.0 * value / total
            r = rows[cusip]; r["managers"].add(f.manager); r["agg"] += w; r["max"] = max(r["max"], w); r["rec"] += w * rf; r["issuer"] = issuer_by[cusip]
    ranked = []
    for cusip, r in rows.items():
        cnt = len(r["managers"])
        if cnt < 2 and r["max"] < 4: continue
        score = 3 * math.log1p(cnt) + .5 * math.log1p(r["agg"]) + .5 * math.log1p(r["rec"])
        nm = norm_name(r["issuer"])
        ranked.append({"cusip": cusip, "issuer": r["issuer"], "norm": nm, "symbol": aliases.get(nm), "managerCount": cnt, "aggregateWeight": r["agg"], "maxWeight": r["max"], "recencyWeight": r["rec"], "score": score})
    ranked.sort(key=lambda x: (-x["score"], -x["managerCount"], -x["aggregateWeight"], x["cusip"]))
    mapped = [x for x in ranked if x["symbol"]]
    # Do NOT promote mapped names from deep ranks into Top80. Mapping coverage is measured separately.
    top_raw = ranked[:TOP_N]
    top_symbols = [x["symbol"] for x in top_raw if x["symbol"]]
    return top_raw, top_symbols, ranked


def main():
    CACHE.mkdir(parents=True, exist_ok=True); OUT.parent.mkdir(parents=True, exist_ok=True)
    aliases, ambiguous = load_aliases()
    print(f"aliases unique={len(aliases)} ambiguous={len(ambiguous)}")
    links = sec_zip_links()
    if not links: raise RuntimeError("No SEC 13F ZIP links discovered")
    print(f"SEC datasets selected={len(links)}")
    filings = []
    for i, (label, url) in enumerate(reversed(links), 1):
        fn = url.rsplit("/", 1)[-1]; p = CACHE / fn
        if not p.exists():
            print(f"download {i}/{len(links)} {label}: {fn}", flush=True)
            p.write_bytes(req(url)); time.sleep(.12)
        try:
            fs = parse_zip(p); filings.extend(fs); print(f"parsed {fn}: filings={len(fs)} total={len(filings)}", flush=True)
        except Exception as e:
            print(f"WARN parse failed {fn}: {e}", file=sys.stderr)
    np = nport_by_month(); results = []
    for month, asof in month_end_dates():
        top_raw, syms, ranked = build_13f_universe(filings, asof, aliases)
        target = np.get(month, [])[:TOP_N]
        a, b = set(syms), set(target)
        overlap = len(a & b)
        raw_mapped = len(syms)
        results.append({"month": month, "asOf": asof, "nportCount": len(target), "raw13fTopCount": len(top_raw), "mapped13fTopCount": raw_mapped, "mappingCoverageTop80": raw_mapped / TOP_N, "intersection": overlap, "overlapVsNport": overlap / len(b) if b else None, "jaccardOnMapped": overlap / len(a | b) if (a | b) else None, "mapped13fTopSymbols": syms, "nportSymbols": target, "unmatched13fTop": [{k:x[k] for k in ("cusip","issuer","managerCount","score")} for x in top_raw if not x["symbol"]][:20]})
        print(f"{month} mapped={raw_mapped}/{TOP_N} overlap={overlap}/{len(target)} ({(overlap/len(target) if target else 0):.3f})")
    cov = [r["mappingCoverageTop80"] for r in results]
    ov = [r["overlapVsNport"] for r in results if r["overlapVsNport"] is not None]
    summary = {"method":"Free SEC Form 13F institutional-breadth proxy vs production N-PORT Top80; point-in-time by filing date; production score formula reused; issuer-name ticker mapping from repository N-PORT/profile data; no deep-rank promotion for unmapped Top80 names.", "period":{"startYear":START_YEAR,"endYear":END_YEAR}, "secDatasetCount":len(links), "filingsParsed":len(filings), "aliasCount":len(aliases), "months":len(results), "mappingCoverageTop80":{"mean":statistics.mean(cov) if cov else None,"median":statistics.median(cov) if cov else None,"min":min(cov) if cov else None}, "overlapVsNport":{"mean":statistics.mean(ov) if ov else None,"median":statistics.median(ov) if ov else None,"min":min(ov) if ov else None,"max":max(ov) if ov else None}, "results":results, "limitations":["13F manager population is broader than N-PORT eligible thematic ETF population; this is a proxy validation, not an identical reconstruction.","13F structured datasets start in July 2013; extending before then requires parsing legacy EDGAR 13F text filings.","Issuer-name mapping intentionally leaves ambiguous/unmatched names unresolved, so low mapping coverage cannot be interpreted as true universe disagreement."]}
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k:v for k,v in summary.items() if k != "results"}, ensure_ascii=False))
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
