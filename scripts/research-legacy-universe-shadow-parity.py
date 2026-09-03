#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "data/sec-nport/bootstrap.json.gz"
HISTORY = ROOT / "data/universe-history.json"
OUT = ROOT / "data/research/legacy-universe-shadow-parity.json"

STRUCTURED_OR_INCOME = re.compile(r"\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b", re.I)
BROAD_BENCHMARK = re.compile(r"\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b", re.I)


def norm(raw: str) -> str:
    s = (raw or "").upper().replace("&", " AND ")
    s = re.sub(r"\b(INCORPORATED|INCORPORATION)\b", "INC", s)
    s = re.sub(r"\b(CORPORATION|CORPORA?TION)\b", "CORP", s)
    s = re.sub(r"\bCOMPANY\b", "CO", s)
    s = re.sub(r"\bLIMITED\b", "LTD", s)
    s = re.sub(r"\bHLDGS\b", "HOLDINGS", s)
    s = re.sub(r"\bPHARMACEUTICALS\b", "PHARMACEUTICAL", s)
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", s).split())


def aliases(raw: str) -> list[str]:
    n = norm(raw)
    out = [n] if n else []
    if n.startswith("THE "):
        out.append(n[4:])
    if n.endswith(" THE"):
        out.append(n[:-4])
    return list(dict.fromkeys(x for x in out if x))


def eligible(filing: dict) -> bool:
    name = filing.get("seriesName", "")
    if STRUCTURED_OR_INCOME.search(name) or BROAD_BENCHMARK.search(name):
        return False
    hs = sorted((h for h in filing.get("holdings", []) if float(h.get("weight") or 0) > 0), key=lambda h: -float(h.get("weight") or 0))
    if len(hs) < 10 or len(hs) > 120:
        return False
    total = sum(float(h.get("weight") or 0) for h in hs)
    top10 = sum(float(h.get("weight") or 0) for h in hs[:10])
    return total >= 50 and top10 >= 25


def latest_sources(filings: list[dict], as_of: str) -> list[dict]:
    latest: dict[str, dict] = {}
    for f in filings:
        if f.get("filingDate", "") > as_of:
            continue
        sid = f.get("seriesId", "")
        cur = latest.get(sid)
        if cur is None or (f.get("filingDate", ""), f.get("accession", "")) > (cur.get("filingDate", ""), cur.get("accession", "")):
            latest[sid] = f
    return [f for f in latest.values() if eligible(f)]


def age_days(as_of: str, filed: str) -> int:
    from datetime import date
    return max(0, (date.fromisoformat(as_of) - date.fromisoformat(filed)).days)


def score_sources(sources: list[dict], resolver=None) -> list[dict]:
    rows: dict[str, dict] = {}
    for f in sources:
        recency = math.exp(-age_days(CURRENT_AS_OF, f["filingDate"]) / 120)
        for h in f.get("holdings", []):
            w = float(h.get("weight") or 0)
            if w <= 0:
                continue
            symbol = h.get("symbol", "").strip().upper() if resolver is None else resolver(f, h)
            if not symbol:
                continue
            row = rows.setdefault(symbol, {"seriesIds": set(), "aggregateWeight": 0.0, "maxWeight": 0.0, "recencyWeight": 0.0})
            row["seriesIds"].add(f["seriesId"])
            row["aggregateWeight"] += w
            row["maxWeight"] = max(row["maxWeight"], w)
            row["recencyWeight"] += w * recency
    out = []
    for symbol, row in rows.items():
        etf_count = len(row["seriesIds"])
        if etf_count < 2 and row["maxWeight"] < 4:
            continue
        score = 3 * math.log1p(etf_count) + 0.5 * math.log1p(row["aggregateWeight"]) + 0.5 * math.log1p(row["recencyWeight"])
        out.append({"symbol": symbol, "etfCount": etf_count, "aggregateWeight": row["aggregateWeight"], "maxWeight": row["maxWeight"], "recencyWeight": row["recencyWeight"], "universeScore": score})
    out.sort(key=lambda x: (-x["universeScore"], -x["etfCount"], -x["aggregateWeight"], x["symbol"]))
    for i, x in enumerate(out[:80], 1):
        x["universeRank"] = i
    return out[:80]


def build_identity_master(filings: list[dict], as_of: str):
    by_alias: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for f in filings:
        if f.get("filingDate", "") > as_of:
            continue
        sid = f.get("seriesId", "")
        for h in f.get("holdings", []):
            sym = h.get("symbol", "").strip().upper()
            issuer = h.get("issuerName", "")
            if not sym or not issuer:
                continue
            for a in aliases(issuer):
                by_alias[a][sym].add(sid)
    return by_alias


def make_resolver(master):
    def resolve(filing: dict, holding: dict) -> str:
        sid = filing.get("seriesId", "")
        issuer = holding.get("issuerName", "")
        for a in aliases(issuer):
            candidates = []
            for sym, series_ids in master.get(a, {}).items():
                if any(other != sid for other in series_ids):
                    candidates.append(sym)
            candidates = sorted(set(candidates))
            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) > 1:
                return ""
        return ""
    return resolve


def corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    dx = [x - mx for x in xs]; dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return sum(x*y for x, y in zip(dx, dy)) / den if den else None


def history_months(raw) -> list[dict]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("months", "history"):
            if isinstance(raw.get(key), list):
                return raw[key]
        return [v for v in raw.values() if isinstance(v, dict) and v.get("signalMonth")]
    return []


CURRENT_AS_OF = "2020-01-01"


def main() -> None:
    global CURRENT_AS_OF
    with gzip.open(BOOT, "rt", encoding="utf-8") as f:
        boot = json.load(f)
    filings = boot.get("snapshots", []) if isinstance(boot, dict) else boot
    raw_history = json.loads(HISTORY.read_text())
    months = sorted((m for m in history_months(raw_history) if "2020-01" <= m.get("signalMonth", "") <= "2020-12"), key=lambda m: m["signalMonth"])
    if len(months) != 12:
        raise RuntimeError(f"Expected 12 Production months for 2020, found {len(months)}")

    monthly = []
    all_top2_hits = 0
    all_top2_total = 0
    both_top2_months = 0
    for prod in months:
        CURRENT_AS_OF = prod["asOf"]
        sources = latest_sources(filings, CURRENT_AS_OF)
        canonical = score_sources(sources)
        stored = [x["symbol"] for x in prod.get("symbols", [])[:80]]
        canon_syms = [x["symbol"] for x in canonical]
        if stored != canon_syms:
            common = len(set(stored) & set(canon_syms))
            raise RuntimeError(f"{prod['signalMonth']}: local canonical reconstruction is not exact stored={len(stored)} calc={len(canon_syms)} common={common}")

        k = len(stored)
        if k < 1:
            raise RuntimeError(f"{prod['signalMonth']}: empty Production Universe")
        master = build_identity_master(filings, CURRENT_AS_OF)
        resolver = make_resolver(master)
        shadow = score_sources(sources, resolver)
        shadow_syms = [x["symbol"] for x in shadow]
        common = set(stored) & set(shadow_syms)
        overlap = len(common) / k
        prod_rank = {s: i + 1 for i, s in enumerate(stored)}
        shadow_rank = {s: i + 1 for i, s in enumerate(shadow_syms)}
        spearman = corr([prod_rank[s] for s in common], [shadow_rank[s] for s in common])
        top2 = stored[:2]
        hits = sum(s in set(shadow_syms) for s in top2)
        all_top2_hits += hits; all_top2_total += len(top2)
        if len(top2) == 2 and hits == 2:
            both_top2_months += 1
        mapped_weight = 0.0; total_weight = 0.0; mapped_count = 0; total_count = 0
        for src in sources:
            for h in src.get("holdings", []):
                w = float(h.get("weight") or 0)
                if w <= 0:
                    continue
                total_count += 1; total_weight += w
                if resolver(src, h):
                    mapped_count += 1; mapped_weight += w
        row = {
            "signalMonth": prod["signalMonth"], "asOf": CURRENT_AS_OF,
            "productionUniverseSize": k, "sourceFilings": len(sources),
            "topKOverlap": overlap, "commonNames": len(common),
            "spearmanCommonRanks": spearman,
            "productionTop2": top2, "top2Hits": hits,
            "identityMappingCountRate": mapped_count / total_count if total_count else None,
            "identityMappingWeightRate": mapped_weight / total_weight if total_weight else None,
        }
        monthly.append(row)
        print("MONTH", json.dumps(row), flush=True)

    overlaps = [x["topKOverlap"] for x in monthly]
    spears = [x["spearmanCommonRanks"] for x in monthly if x["spearmanCommonRanks"] is not None]
    summary = {
        "purpose": "Preregistered Gate A shadow parity. Production symbols are hidden from candidate holdings and recovered only through point-in-time cross-series issuer identity evidence. No strategy returns used.",
        "months": len(monthly),
        "productionUniverseSizes": [x["productionUniverseSize"] for x in monthly],
        "medianTopKOverlap": statistics.median(overlaps),
        "minimumTopKOverlap": min(overlaps),
        "medianSpearmanCommonRanks": statistics.median(spears) if spears else None,
        "productionTop2IndividualRetention": all_top2_hits / all_top2_total if all_top2_total else None,
        "bothProductionTop2RetainedMonthRate": both_top2_months / len(monthly),
        "thresholds": {"medianTopKOverlap": 0.80, "minimumTopKOverlap": 0.70, "medianSpearmanCommonRanks": 0.75, "productionTop2IndividualRetention": 0.80, "bothProductionTop2RetainedMonthRate": 0.70},
        "monthly": monthly,
    }
    checks = {k: summary[k] >= v for k, v in summary["thresholds"].items()}
    summary["checks"] = checks
    summary["gateA"] = "PASS" if all(checks.values()) else "FAIL"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "monthly"}), flush=True)


if __name__ == "__main__":
    main()
