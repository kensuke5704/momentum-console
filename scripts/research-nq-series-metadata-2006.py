#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import urllib.error
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
STRONG_ETF_REGISTRANT = re.compile(r"ISHARES|STREETTRACKS|SELECT SECTOR SPDR|SPDR TRUST|POWERSHARES EXCHANGE TRADED|RYDEX ETF TRUST|PROSHARES", re.I)
VANGUARD_ETF_CANDIDATE = re.compile(r"VANGUARD.*(?:INDEX|WORLD|WHITEHALL|MALVERN)", re.I)
ETF_TEXT = re.compile(r"(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED", re.I)
ETF_CLASS = re.compile(r"ETF\s+SHARES?|EXCHANGE[ -]TRADED", re.I)


def sec_url(filename: str) -> str:
    return "https://www.sec.gov/Archives/" + filename.lstrip("/")


def fetch_prefix(url: str) -> tuple[str, str]:
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request("https://r.jina.ai/" + url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return "jina", r.read(1_500_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code != 429:
                raise
        except Exception as e:
            last = e
        time.sleep(5 * (attempt + 1))
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
    for block in re.findall(r"(?is)<SERIES>(.*?)</SERIES>", text):
        series_id = tag_value(block, "SERIES-ID")
        series_name = tag_value(block, "SERIES-NAME")
        classes = []
        for cb in re.findall(r"(?is)<CLASS-CONTRACT>(.*?)</CLASS-CONTRACT>", block):
            classes.append({
                "id": tag_value(cb, "CLASS-CONTRACT-ID"),
                "name": tag_value(cb, "CLASS-CONTRACT-NAME"),
                "ticker": tag_value(cb, "CLASS-CONTRACT-TICKER-SYMBOL"),
            })
        explicit_series = bool(series_name and ETF_TEXT.search(series_name))
        strong_registrant = bool(STRONG_ETF_REGISTRANT.search(company))
        etf_classes = [c for c in classes if c.get("name") and ETF_CLASS.search(c["name"])]
        is_etf = explicit_series or strong_registrant or bool(etf_classes)
        etf_tickers = []
        for c in classes:
            if not c.get("ticker"):
                continue
            if explicit_series or strong_registrant or (c.get("name") and ETF_CLASS.search(c["name"])):
                etf_tickers.append(c["ticker"].upper())
        out.append({
            "seriesId": series_id,
            "seriesName": series_name,
            "classes": classes,
            "explicitSeriesEtf": explicit_series,
            "strongEtfRegistrant": strong_registrant,
            "isEtf": is_etf,
            "etfTickers": list(dict.fromkeys(etf_tickers)),
        })
    return out


def choose_samples(filings: list[dict]) -> list[dict]:
    nq = [x for x in filings if x.get("form") == "N-Q"]
    chosen: list[dict] = []
    seen: set[str] = set()

    def add_matching(pattern: re.Pattern[str], limit: int) -> None:
        added = 0
        for x in nq:
            company = str(x.get("company") or "")
            cik = str(x.get("cik") or "")
            if cik and cik not in seen and pattern.search(company):
                chosen.append(x)
                seen.add(cik)
                added += 1
                if added >= limit:
                    break

    add_matching(STRONG_ETF_REGISTRANT, 12)
    add_matching(VANGUARD_ETF_CANDIDATE, 6)
    return chosen


def inspect_one(i: int, x: dict) -> dict:
    url = sec_url(x["filename"])
    try:
        method, text = fetch_prefix(url)
        series = parse_series_contracts(text, str(x.get("company") or ""))
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
            "seriesNames": values(text, "SERIES-NAME")[:120],
            "tickers": values(text, "CLASS-CONTRACT-TICKER-SYMBOL")[:160],
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
    for i, x in enumerate(samples, 1):
        r = inspect_one(i, x)
        results.append(r)
        if "error" in r:
            print(f"{i}/{len(samples)} FAIL {r.get('company')} {r['error']}", flush=True)
        else:
            print(
                f"{i}/{len(samples)} {r['company'][:42]} blocks={r['seriesBlockCount']} "
                f"series={len(r['seriesNames'])} tickers={len(r['tickers'])} "
                f"etfSeries={len(r['classifiedEtfSeries'])} etfTickers={len(r['classifiedEtfTickers'])}",
                flush=True,
            )
            if r["classifiedEtfTickers"]:
                print("  ETF_TICKERS", json.dumps(r["classifiedEtfTickers"][:30]), flush=True)
        if i < len(samples):
            time.sleep(3.2)

    ok = [r for r in results if "error" not in r]
    methods = Counter(r["method"] for r in ok)
    with_series = [r for r in ok if r["seriesNames"]]
    with_ticker = [r for r in ok if r["tickers"]]
    with_structured_series = [r for r in ok if r["seriesBlockCount"] > 0]
    with_etf = [r for r in ok if r["classifiedEtfSeries"]]
    with_etf_ticker = [r for r in ok if r["classifiedEtfTickers"]]
    summary = {
        "year": 2006,
        "sampleRule": "Distinct filing-time ETF registrants (max 12) plus Vanguard ETF-share-class candidates (max 6). No performance-based selection.",
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
