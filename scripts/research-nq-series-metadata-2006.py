#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "data" / "research" / "nq-index-2006.json"
OUT = ROOT / "data" / "research" / "nq-series-metadata-2006.json"
UA = {
    "User-Agent": "momentum-console research kensuke5704@users.noreply.github.com",
    "Accept": "text/plain,text/html,*/*",
}
ETF_HINT = re.compile(r"ETF|EXCHANGE[ -]TRADED|ISHARES|STREETTRACKS|SPDR|POWERSHARES|RYDEX|VANGUARD|PROSHARES", re.I)
STRONG_ETF_REGISTRANT = re.compile(r"ISHARES|STREETTRACKS|SELECT SECTOR SPDR|SPDR TRUST|POWERSHARES EXCHANGE TRADED|RYDEX ETF TRUST|PROSHARES", re.I)
ETF_TEXT = re.compile(r"(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED", re.I)
ETF_CLASS = re.compile(r"ETF\s+SHARES?|EXCHANGE[ -]TRADED", re.I)


def sec_url(filename: str) -> str:
    return "https://www.sec.gov/Archives/" + filename.lstrip("/")


def fetch_prefix(url: str) -> tuple[str, str]:
    # GitHub-hosted runners are blocked by SEC Archives in this environment.
    # Jina is only a transport bridge; the underlying URL remains the SEC filing.
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://r.jina.ai/" + url, headers=UA)
            with urllib.request.urlopen(req, timeout=35) as r:
                return "jina", r.read(1_500_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code != 429:
                raise
        except Exception as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    assert last is not None
    raise last


def tag_value(text: str, tag: str) -> str | None:
    m = re.search(rf"(?im)<{re.escape(tag)}>\s*([^\r\n<]+)", text)
    return " ".join(m.group(1).split()) if m else None


def values(text: str, tag: str) -> list[str]:
    out = []
    for m in re.finditer(rf"(?im)<{re.escape(tag)}>\s*([^\r\n<]+)", text):
        v = " ".join(m.group(1).split())
        if v and v not in out:
            out.append(v)
    return out


def parse_series_contracts(text: str, company: str) -> list[dict]:
    out: list[dict] = []
    blocks = re.findall(r"(?is)<SERIES>(.*?)</SERIES>", text)
    for block in blocks:
        series_id = tag_value(block, "SERIES-ID")
        series_name = tag_value(block, "SERIES-NAME")
        classes = []
        class_blocks = re.findall(r"(?is)<CLASS-CONTRACT>(.*?)</CLASS-CONTRACT>", block)
        for cb in class_blocks:
            classes.append({
                "id": tag_value(cb, "CLASS-CONTRACT-ID"),
                "name": tag_value(cb, "CLASS-CONTRACT-NAME"),
                "ticker": tag_value(cb, "CLASS-CONTRACT-TICKER-SYMBOL"),
            })
        explicit_series = bool(series_name and ETF_TEXT.search(series_name))
        explicit_class = any(c.get("name") and ETF_CLASS.search(c["name"]) for c in classes)
        strong_registrant = bool(STRONG_ETF_REGISTRANT.search(company))
        is_etf = explicit_series or explicit_class or strong_registrant
        etf_tickers = [c["ticker"].upper() for c in classes if c.get("ticker") and (explicit_series or strong_registrant or (c.get("name") and ETF_CLASS.search(c["name"])))]
        out.append({
            "seriesId": series_id,
            "seriesName": series_name,
            "classes": classes,
            "explicitSeriesEtf": explicit_series,
            "explicitClassEtf": explicit_class,
            "strongEtfRegistrant": strong_registrant,
            "isEtf": is_etf,
            "etfTickers": list(dict.fromkeys(etf_tickers)),
        })
    return out


def choose_samples(filings: list[dict]) -> list[dict]:
    nq = [x for x in filings if x.get("form") == "N-Q"]
    hinted = [x for x in nq if ETF_HINT.search(str(x.get("company") or ""))]
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


def inspect_one(i: int, x: dict) -> dict:
    url = sec_url(x["filename"])
    try:
        method, text = fetch_prefix(url)
        series = parse_series_contracts(text, str(x.get("company") or ""))
        flat_series_names = values(text, "SERIES-NAME")
        flat_tickers = values(text, "CLASS-CONTRACT-TICKER-SYMBOL")
        etf_series = [s for s in series if s["isEtf"]]
        etf_tickers = list(dict.fromkeys(t for s in etf_series for t in s["etfTickers"]))
        return {
            "index": i,
            "cik": x["cik"],
            "company": x["company"],
            "dateFiled": x["dateFiled"],
            "filename": x["filename"],
            "method": method,
            "seriesBlockCount": len(series),
            "seriesNames": flat_series_names[:120],
            "tickers": flat_tickers[:160],
            "classifiedEtfSeries": etf_series[:120],
            "classifiedEtfTickers": etf_tickers[:160],
        }
    except Exception as e:
        return {
            "index": i,
            "cik": x.get("cik"),
            "company": x.get("company"),
            "dateFiled": x.get("dateFiled"),
            "filename": x.get("filename"),
            "error": repr(e),
        }


def main() -> None:
    idx = json.loads(IDX.read_text())
    samples = choose_samples(idx["filings"])
    print(f"samples={len(samples)}", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(inspect_one, i, x) for i, x in enumerate(samples, 1)]
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            if "error" in r:
                print(f"{r['index']}/{len(samples)} FAIL {r.get('company')} {r['error']}", flush=True)
            else:
                print(
                    f"{r['index']}/{len(samples)} {r['company'][:38]} blocks={r['seriesBlockCount']} "
                    f"series={len(r['seriesNames'])} tickers={len(r['tickers'])} "
                    f"etfSeries={len(r['classifiedEtfSeries'])} etfTickers={len(r['classifiedEtfTickers'])}",
                    flush=True,
                )
                if r["classifiedEtfTickers"]:
                    print("  ETF_TICKERS", json.dumps(r["classifiedEtfTickers"][:20]), flush=True)
    results.sort(key=lambda r: r["index"])

    ok = [r for r in results if "error" not in r]
    methods = Counter(r["method"] for r in ok)
    with_series = [r for r in ok if r["seriesNames"]]
    with_ticker = [r for r in ok if r["tickers"]]
    with_structured_series = [r for r in ok if r["seriesBlockCount"] > 0]
    with_etf = [r for r in ok if r["classifiedEtfSeries"]]
    with_etf_ticker = [r for r in ok if r["classifiedEtfTickers"]]
    summary = {
        "year": 2006,
        "sampleRule": "Up to 36 distinct ETF-hint registrants plus 24 deterministic broad N-Q samples. Classification uses only filing-time registrant, series, class and ticker metadata.",
        "sampleCount": len(samples),
        "fetchSuccess": len(ok),
        "fetchRate": len(ok) / len(samples) if samples else None,
        "fetchMethods": dict(methods),
        "seriesMetadataRate": len(with_series) / len(ok) if ok else None,
        "tickerMetadataRate": len(with_ticker) / len(ok) if ok else None,
        "structuredSeriesRate": len(with_structured_series) / len(ok) if ok else None,
        "classifiedEtfRegistrantRate": len(with_etf) / len(ok) if ok else None,
        "classifiedEtfTickerRate": len(with_etf_ticker) / len(ok) if ok else None,
        "classifiedEtfTickers": sorted(set(t for r in ok for t in r["classifiedEtfTickers"])),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
