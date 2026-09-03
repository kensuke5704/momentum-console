#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIT = ROOT / "data/research/nq-pit-holdings-2006-ec-filtered.json"
MAPPING = ROOT / "data/research/nq-npx-mapping-2006.json"
OUT = ROOT / "data/research/nq-country-cins-2006.json"

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts" / "research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)

# Exact same fixed complete-submission sources and explicit-series segmentation path used by the accepted corrected PIT diagnostics.
SOURCES = [
    {"company": "SELECT SECTOR SPDR TRUST", "cik": "1064641", "filename": "edgar/data/1064641/0000950135-06-001225.txt"},
    {"company": "RYDEX ETF TRUST", "cik": "1208211", "filename": "edgar/data/1208211/0000950135-06-001815.txt"},
    {"company": "STREETTRACKS SERIES TRUST", "cik": "1064642", "filename": "edgar/data/1064642/0000950135-06-003650.txt"},
]

COUNTRIES = {
    "ARGENTINA", "AUSTRALIA", "AUSTRIA", "BELGIUM", "BRAZIL", "CANADA", "CHILE", "CHINA",
    "DENMARK", "FINLAND", "FRANCE", "GERMANY", "HONG KONG", "INDIA", "IRELAND", "ISRAEL", "ITALY",
    "JAPAN", "MEXICO", "NETHERLANDS", "NORWAY", "PORTUGAL", "SINGAPORE", "SOUTH AFRICA", "SOUTH KOREA",
    "SPAIN", "SWEDEN", "SWITZERLAND", "TAIWAN", "UNITED KINGDOM", "UNITED STATES",
}
COUNTRY_LINE = re.compile(r"\b([A-Z][A-Z .&'-]{2,40})\s*(?:--|[-–—])\s*([0-9]+(?:\.[0-9]+)?)\s*%", re.I)
CINS_NON_US = set("ABCDEFGHJKLMNPQRSTVWXYZ") - {"U"}


def norm(s: str) -> str:
    s=re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", s, flags=re.I)
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", s.upper()).split())


def series_country_streams() -> dict[str, list[tuple[str,str]]]:
    streams={}
    for source in SOURCES:
        _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(source["filename"]))
        series = seg.meta.parse_series_contracts(submission, source["company"])
        etf = [s for s in series if s["isEtf"]]
        _, text = seg.embedded_primary_nq(submission)
        grouped, _ = seg.grouped_schedule_blocks(text, etf)
        for sid, blocks in grouped.items():
            combined="\n".join(blocks)
            vis=seg.visible(combined)
            state="UNKNOWN"; rows=[]
            for raw in vis.splitlines():
                line=" ".join(raw.split()).strip()
                if not line: continue
                m=COUNTRY_LINE.search(line.upper())
                if m:
                    name=" ".join(m.group(1).split()).strip(" .-")
                    if name in COUNTRIES:
                        state="US" if name=="UNITED STATES" else "NON_US"
                        continue
                if re.search(r"\b(?:SHORT[- ]TERM INVESTMENTS?|MONEY MARKET|NET ASSETS)\b", line, re.I):
                    state="UNKNOWN"
                rows.append((norm(line),state))
            streams[sid]=rows
    return streams


def locate(desc: str, rows: list[tuple[str,str]]) -> str:
    q=norm(desc)
    if not q:return "UNKNOWN"
    hits=[]
    # First exact normalized containment; then a conservative first-4-token anchor for HTML column fragmentation.
    for text,state in rows:
        if state!="UNKNOWN" and q in text:hits.append(state)
    if not hits:
        toks=q.split(); anchor=" ".join(toks[:min(4,len(toks))])
        if len(anchor)>=6:
            for text,state in rows:
                if state!="UNKNOWN" and anchor in text:hits.append(state)
    return hits[0] if hits and all(x==hits[0] for x in hits) else "UNKNOWN"


def main() -> None:
    pit=json.loads(PIT.read_text()); mapping=json.loads(MAPPING.read_text())
    by_key={(d.get("seriesId"),d.get("reportDate"),d.get("description")):d for d in mapping.get("details",[])}
    streams=series_country_streams()
    results=[];counts=Counter();weights=defaultdict(float);methods=Counter();method_weights=defaultdict(float)
    for record in pit["records"]:
        rows=streams.get(record.get("seriesId"),[])
        for h in record["holdings"]:
            desc=h["description"];w=float(h.get("weight") or 0)
            country=locate(desc,rows);method="NQ_EXPLICIT_COUNTRY_SECTION" if country!="UNKNOWN" else None
            d=by_key.get((record.get("seriesId"),record.get("reportDate"),desc)); security_id=None;ticker=None
            if d and d.get("status")=="MATCHED_UNIQUE" and len(d.get("identities",[]))==1:
                ticker=d["identities"][0]["ticker"];security_id=d["identities"][0]["securityId"]
            if country=="UNKNOWN" and security_id and len(security_id)==9 and security_id[0].isalpha() and security_id[0].upper() in CINS_NON_US:
                country="NON_US";method="CINS_NON_US"
            counts[country]+=1;weights[country]+=w
            if method:methods[method]+=1;method_weights[method]+=w
            results.append({"seriesId":record.get("seriesId"),"seriesName":record.get("seriesName"),"fundTickers":record.get("fundTickers",[]),"reportDate":record.get("reportDate"),"description":desc,"weight":w,"ticker":ticker,"securityId":security_id,"classification":country,"method":method})
    total=len(results);total_w=sum(r["weight"] for r in results)
    out={"year":2006,"purpose":"Structural point-in-time US/NON_US attribution using corrected explicit-series N-Q country sections plus official CINS country-prefix semantics. No returns, rankings, current domicile, or listing venue used.","sourceRule":"Same fixed complete submissions and exact-series grouping as corrected 2006 PIT; holdings/industry words never determine series identity.","rules":["Explicit N-Q country heading is highest-priority PIT evidence; UNITED STATES -> US, other recognized country -> NON_US.","If no explicit country evidence and uniquely mapped security ID is CINS, any non-U alphabetic prefix -> NON_US.","Numeric CUSIP is never treated as US because conventional CUSIP includes Canadian securities; CINS U is not used as positive US proof here.","Remaining holdings stay UNKNOWN."],"holdingCount":total,"holdingWeight":total_w,"classificationCounts":dict(counts),"classificationWeights":dict(weights),"resolvedCountRate":(counts['US']+counts['NON_US'])/total if total else None,"resolvedWeightRate":(weights['US']+weights['NON_US'])/total_w if total_w else None,"methods":dict(methods),"methodWeights":dict(method_weights),"results":results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+"\n")
    print("SUMMARY",json.dumps({k:v for k,v in out.items() if k!="results"}),flush=True)
    for r in results:
        if r["classification"]!="UNKNOWN":print("RESOLVED",json.dumps(r),flush=True)

if __name__=="__main__":main()
