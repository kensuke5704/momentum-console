#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "data" / "research" / "nq-index-2006.json"
OUT = ROOT / "data" / "research" / "nq-series-metadata-2006.json"
UA = {
    "User-Agent": "momentum-console research kensuke5704@users.noreply.github.com",
    "Accept": "text/plain,text/html,*/*",
}
ETF_HINT = re.compile(r"ETF|EXCHANGE[ -]TRADED|ISHARES|STREETTRACKS|SPDR|POWERSHARES|RYDEX|VANGUARD|PROSHARES", re.I)


def sec_url(filename: str) -> str:
    return "https://www.sec.gov/Archives/" + filename.lstrip("/")


def fetch_prefix(url: str) -> tuple[str, str]:
    # The SEC SGML header is at the front of the filing and is the only part needed here.
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return "sec-direct", r.read(1_500_000).decode("utf-8", "replace")
    except Exception:
        req = urllib.request.Request("https://r.jina.ai/" + url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            return "jina", r.read(1_500_000).decode("utf-8", "replace")


def values(text: str, tag: str) -> list[str]:
    # Legacy EDGAR submissions commonly use SGML tags without explicit closing tags.
    out = []
    for m in re.finditer(rf"(?im)<{re.escape(tag)}>\s*([^\r\n<]+)", text):
        v = " ".join(m.group(1).split())
        if v and v not in out:
            out.append(v)
    return out


def choose_samples(filings: list[dict]) -> list[dict]:
    nq = [x for x in filings if x.get("form") == "N-Q"]
    hinted = [x for x in nq if ETF_HINT.search(str(x.get("company") or ""))]
    # Keep all distinct hinted registrants up to 36 filings, then add a deterministic broad sample.
    chosen: list[dict] = []
    seen_cik: set[str] = set()
    for x in hinted:
        cik = str(x.get("cik") or "")
        if cik and cik not in seen_cik:
            chosen.append(x)
            seen_cik.add(cik)
        if len(chosen) >= 36:
            break
    if nq:
        for i in range(24):
            x = nq[min(len(nq) - 1, (i * len(nq)) // 24)]
            key = (x.get("cik"), x.get("filename"))
            if not any((y.get("cik"), y.get("filename")) == key for y in chosen):
                chosen.append(x)
    return chosen


def main() -> None:
    idx = json.loads(IDX.read_text())
    samples = choose_samples(idx["filings"])
    print(f"samples={len(samples)}", flush=True)
    results = []
    methods = Counter()
    for i, x in enumerate(samples, 1):
        url = sec_url(x["filename"])
        try:
            method, text = fetch_prefix(url)
            methods[method] += 1
            series_names = values(text, "SERIES-NAME")
            series_ids = values(text, "SERIES-ID")
            class_names = values(text, "CLASS-CONTRACT-NAME")
            tickers = values(text, "CLASS-CONTRACT-TICKER-SYMBOL")
            etf_series = [s for s in series_names if re.search(r"(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED", s, re.I)]
            r = {
                "cik": x["cik"],
                "company": x["company"],
                "dateFiled": x["dateFiled"],
                "filename": x["filename"],
                "method": method,
                "seriesNames": series_names[:80],
                "seriesIds": series_ids[:80],
                "classNames": class_names[:80],
                "tickers": tickers[:80],
                "etfSeriesNames": etf_series[:80],
                "containsEtfText": bool(re.search(r"(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED", text, re.I)),
            }
            print(
                f"{i}/{len(samples)} {x['dateFiled']} {x['company'][:36]} method={method} "
                f"series={len(series_names)} tickers={len(tickers)} etfSeries={len(etf_series)}",
                flush=True,
            )
            if series_names:
                print("  SERIES", json.dumps(series_names[:6]), flush=True)
            if tickers:
                print("  TICKERS", json.dumps(tickers[:12]), flush=True)
        except Exception as e:
            r = {
                "cik": x.get("cik"),
                "company": x.get("company"),
                "dateFiled": x.get("dateFiled"),
                "filename": x.get("filename"),
                "error": repr(e),
            }
            print(f"{i}/{len(samples)} FAIL {x.get('company')} {e!r}", flush=True)
        results.append(r)
        time.sleep(0.12)

    ok = [r for r in results if "error" not in r]
    with_series = [r for r in ok if r["seriesNames"]]
    with_ticker = [r for r in ok if r["tickers"]]
    with_etf_series = [r for r in ok if r["etfSeriesNames"]]
    summary = {
        "year": 2006,
        "sampleRule": "Up to 36 distinct ETF-hint registrants plus 24 deterministic broad N-Q samples.",
        "sampleCount": len(samples),
        "fetchSuccess": len(ok),
        "fetchRate": len(ok) / len(samples) if samples else None,
        "fetchMethods": dict(methods),
        "withSeriesMetadata": len(with_series),
        "seriesMetadataRate": len(with_series) / len(ok) if ok else None,
        "withTickerMetadata": len(with_ticker),
        "tickerMetadataRate": len(with_ticker) / len(ok) if ok else None,
        "withExplicitEtfSeriesName": len(with_etf_series),
        "explicitEtfSeriesRate": len(with_etf_series) / len(ok) if ok else None,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
