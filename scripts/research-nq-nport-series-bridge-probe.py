#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "data/sec-nport/bootstrap.json.gz"
OUT = ROOT / "data/research/nq-nport-series-bridge-probe.json"
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "application/json,text/plain,*/*"}
SAMPLE_N = 12


def get_json(url: str):
    last = None
    for candidate in (url, "https://r.jina.ai/http://" + url.removeprefix("https://")):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read(2_000_000).decode("utf-8", "replace")
            return json.loads(raw), candidate
        except Exception as e:
            last = repr(e)
    raise RuntimeError(last or "fetch failed")


def efts_url(series_id: str) -> str:
    params = {
        "q": f'"{series_id}"',
        "dateRange": "custom",
        "startdt": "2018-01-01",
        "enddt": "2019-12-31",
        "forms": "N-Q,N-Q/A",
    }
    return "https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode(params)


def hit_source(hit: dict) -> dict:
    src = hit.get("_source", {}) if isinstance(hit, dict) else {}
    return {
        "fileDate": src.get("file_date"),
        "form": src.get("form"),
        "ciks": src.get("ciks"),
        "adsh": src.get("adsh"),
        "displayNames": src.get("display_names"),
        "fileNum": src.get("file_num"),
    }


def main() -> None:
    with gzip.open(BOOT, "rt", encoding="utf-8") as f:
        boot = json.load(f)
    filings = boot.get("snapshots", [])
    earliest_report = min((x.get("reportDate") for x in filings if x.get("reportDate")), default=None)
    early = [x for x in filings if x.get("reportDate") and x["reportDate"] <= "2019-12-31"]
    by_series = {}
    for row in sorted(early, key=lambda x: (x.get("reportDate", ""), x.get("seriesId", ""))):
        sid = row.get("seriesId")
        if sid and sid not in by_series:
            by_series[sid] = row
    population = sorted(by_series.values(), key=lambda x: (x.get("seriesId", ""), x.get("seriesName", "")))
    n = min(SAMPLE_N, len(population))
    positions = sorted(set(min(len(population)-1, (i*len(population))//n) for i in range(n))) if n else []
    sample = [population[i] for i in positions]
    results = []
    for i, row in enumerate(sample, 1):
        sid = row["seriesId"]
        rec = {"seriesId": sid, "seriesName": row.get("seriesName"), "nportReportDate": row.get("reportDate"), "nportFilingDate": row.get("filingDate")}
        try:
            payload, transport = get_json(efts_url(sid))
            hits = payload.get("hits", {}).get("hits", []) if isinstance(payload, dict) else []
            rec["transport"] = transport
            rec["nqHitCount"] = len(hits)
            rec["hits"] = [hit_source(h) for h in hits[:8]]
        except Exception as e:
            rec["error"] = repr(e)
            rec["nqHitCount"] = 0
        results.append(rec)
        print(f"{i}/{len(sample)}", json.dumps(rec), flush=True)
        time.sleep(0.15)
    found = sum(1 for r in results if r.get("nqHitCount", 0) > 0)
    out = {
        "purpose": "Structural probe for a same-series N-Q to N-PORT transition bridge using SEC series IDs only. No returns, rankings, or strategy outcomes used.",
        "bootstrapEarliestReportDate": earliest_report,
        "earlyNportSeriesPopulation": len(population),
        "sampleRule": "12 equal-quantile positions after deterministic seriesId,seriesName sort among N-PORT filings with reportDate <= 2019-12-31.",
        "sampleCount": len(results),
        "seriesWithHistoricalNqHit": found,
        "hitRate": found / len(results) if results else None,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k:v for k,v in out.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
