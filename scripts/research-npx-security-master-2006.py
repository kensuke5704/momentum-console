#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import tempfile
import time
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "research" / "npx-security-master-pilot-2006.json"
DRIVE = "https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t"
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "text/plain,text/html,*/*"}
TARGET_FORMS = {"N-PX", "N-PX/A"}
TICKER_RE = re.compile(r"\bTICKER\s*:?\s*([A-Z0-9.\-]+)", re.I)
SECURITY_RE = re.compile(r"\bSECURITY\s+ID\s*:?\s*(?:CUSIP9\s+)?([A-Z0-9]{6,14})", re.I)
MEETING_RE = re.compile(r"\bMEETING\s+DATE\s*:?\s*([^|]{6,30}?)(?=\s+(?:TICKER|SECURITY\s+ID|MEETING\s+TYPE|MEETING\s+STATUS|RECORD\s+DATE|$))", re.I)
ISSUER_LABEL_RE = re.compile(r"^ISSUER\s+NAME\s*:\s*(.+)$", re.I)
BAD_ISSUER = re.compile(r"^(?:TICKER|SECURITY ID|MEETING DATE|MEETING STATUS|MEETING TYPE|RECORD DATE|PROPOSAL|VOTE|MGMT|MANAGEMENT|ITEM|PAGE|FORM N-PX)\b", re.I)


def download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        while True:
            b = r.read(1024 * 1024)
            if not b:
                break
            f.write(b)
    print(f"index archive bytes={path.stat().st_size:,}", flush=True)


def filing_index_2006() -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / "master.zip"
        download(DRIVE, zp)
        hits = []
        with zipfile.ZipFile(zp) as z:
            qfiles = sorted(n for n in z.namelist() if re.search(r"master_2006_QTR[1-4]\.idx$", n))
            for name in qfiles:
                text = z.read(name).decode("latin-1", "replace")
                for line in text.splitlines():
                    p = line.split("|")
                    if len(p) < 5:
                        continue
                    cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
                    if form.upper() in TARGET_FORMS and date_filed.startswith("2006"):
                        hits.append({"cik": cik, "company": company, "form": form.upper(), "dateFiled": date_filed, "filename": filename})
        uniq = {(x["cik"], x["form"], x["dateFiled"], x["filename"]): x for x in hits}
        return sorted(uniq.values(), key=lambda x: (x["dateFiled"], x["cik"], x["filename"]))


def choose_samples(filings: list[dict]) -> list[dict]:
    primary = [x for x in filings if x["form"] == "N-PX"]
    if len(primary) <= 4:
        return primary
    return [primary[min(len(primary) - 1, (i * len(primary)) // 4)] for i in range(4)]


def sec_url(filename: str) -> str:
    return "https://www.sec.gov/Archives/" + filename.lstrip("/")


def fetch_text(url: str) -> str:
    req = urllib.request.Request("https://r.jina.ai/" + url, headers=UA)
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read(2_000_000).decode("utf-8", "replace")


def text_lines(text: str) -> list[str]:
    s = re.sub(r"(?is)<BR\s*/?>", "\n", text)
    s = re.sub(r"(?is)</(?:P|DIV|TR|TD|PRE|TABLE|LI|H[1-6])>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return [" ".join(line.split()) for line in s.splitlines() if " ".join(line.split())]


def clean_issuer(raw: str) -> str | None:
    raw = raw.strip(" |-:\t")
    labelled = ISSUER_LABEL_RE.match(raw)
    s = labelled.group(1).strip() if labelled else raw
    s = re.sub(r"^[*#>\-]+\s*", "", s)
    if len(s) < 3 or len(s) > 180 or BAD_ISSUER.search(s):
        return None
    if not re.search(r"[A-Za-z]", s):
        return None
    if re.fullmatch(r"[A-Z ]{1,8}", s) and len(s.split()) <= 2:
        return None
    return s


def issuer_before(lines: list[str], anchor: int) -> str | None:
    # Fidelity-style reports label the issuer explicitly, sometimes two lines before Ticker.
    for j in range(anchor - 1, max(-1, anchor - 8), -1):
        m = ISSUER_LABEL_RE.match(lines[j])
        if m:
            return clean_issuer(lines[j])
    # Broadridge-style reports put the issuer as the closest plain line before Ticker/Security ID.
    for j in range(anchor - 1, max(-1, anchor - 8), -1):
        candidate = clean_issuer(lines[j])
        if candidate:
            return candidate
    return None


def parse_records(text: str) -> list[dict]:
    lines = text_lines(text)
    records = []
    for i, line in enumerate(lines):
        upper = line.upper()
        if "TICKER" not in upper and "SECURITY ID" not in upper:
            continue
        lo = max(0, i - 3)
        hi = min(len(lines), i + 5)
        window = " | ".join(lines[lo:hi])
        ticker_m = TICKER_RE.search(window)
        security_m = SECURITY_RE.search(window)
        if not ticker_m and not security_m:
            continue
        issuer = issuer_before(lines, i)
        if not issuer:
            continue
        meeting_m = MEETING_RE.search(window)
        records.append({
            "issuer": issuer,
            "ticker": ticker_m.group(1).upper() if ticker_m else None,
            "securityId": security_m.group(1).upper() if security_m else None,
            "meetingDateRaw": meeting_m.group(1).strip() if meeting_m else None,
        })
    out = []
    seen = set()
    for r in records:
        key = (r["issuer"].upper(), r.get("ticker"), r.get("securityId"))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main() -> None:
    filings = filing_index_2006()
    form_counts = Counter(x["form"] for x in filings)
    month_counts = Counter(x["dateFiled"][:7] for x in filings)
    print("INDEX", json.dumps({"filings": len(filings), "forms": dict(form_counts), "months": dict(month_counts)}), flush=True)
    samples = choose_samples(filings)
    print(f"samples={len(samples)}", flush=True)
    results = []
    for i, x in enumerate(samples, 1):
        try:
            text = fetch_text(sec_url(x["filename"]))
            records = parse_records(text)
            paired = [r for r in records if r.get("ticker") and r.get("securityId")]
            r = {**x, "bytes": len(text.encode()), "records": len(records), "pairedRecords": len(paired), "sampleRecords": records[:30]}
            print(f"{i}/{len(samples)} {x['dateFiled']} {x['company'][:38]} records={len(records)} paired={len(paired)}", flush=True)
            for rec in paired[:3]:
                print("  ", json.dumps(rec), flush=True)
        except Exception as e:
            r = {**x, "error": repr(e)}
            print(f"{i}/{len(samples)} FAIL {x['company'][:38]} {e!r}", flush=True)
        results.append(r)
        if i < len(samples):
            time.sleep(2.5)

    ok = [r for r in results if "error" not in r]
    counts = sorted(r["pairedRecords"] for r in ok)
    all_records = [record for r in ok for record in r.get("sampleRecords", [])]
    unique_tickers = sorted({r["ticker"] for r in all_records if r.get("ticker")})
    unique_ids = sorted({r["securityId"] for r in all_records if r.get("securityId")})
    def rate(pred):
        return sum(1 for r in ok if pred(r)) / len(ok) if ok else None
    summary = {
        "year": 2006,
        "allNpxFilings": len(filings),
        "formCounts": dict(form_counts),
        "monthCounts": dict(month_counts),
        "sampleRule": "Four deterministic quartile N-PX filings across 2006 filing order; structural feasibility only.",
        "sampleCount": len(samples),
        "fetchSuccess": len(ok),
        "fetchRate": len(ok) / len(samples) if samples else None,
        "atLeast1PairedRecordRate": rate(lambda r: r["pairedRecords"] >= 1),
        "atLeast10PairedRecordsRate": rate(lambda r: r["pairedRecords"] >= 10),
        "atLeast50PairedRecordsRate": rate(lambda r: r["pairedRecords"] >= 50),
        "medianPairedRecords": counts[len(counts) // 2] if counts else None,
        "diagnosticUniqueTickersInSamples": len(unique_tickers),
        "diagnosticUniqueSecurityIdsInSamples": len(unique_ids),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
