#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIT = ROOT / "data/research/nq-pit-holdings-2006-ec-filtered.json"
MAPPING = ROOT / "data/research/nq-npx-mapping-2006.json"
OUT = ROOT / "data/research/nq-country-cins-2006.json"
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "text/plain,text/html,*/*"}

SOURCES = {
    "0001193125-06-044766": "https://www.sec.gov/Archives/edgar/data/1064642/000119312506044766/dnq.htm",
    "0001193125-06-067945": "https://www.sec.gov/Archives/edgar/data/1168164/000119312506067945/dnq.htm",
    "0001193125-06-114369": "https://www.sec.gov/Archives/edgar/data/1060523/000119312506114369/dnq.htm",
}

COUNTRY_NAMES = {
    "UNITED STATES":"US","UNITED KINGDOM":"NON_US","SWITZERLAND":"NON_US","JAPAN":"NON_US",
    "FRANCE":"NON_US","GERMANY":"NON_US","ITALY":"NON_US","NETHERLANDS":"NON_US","SOUTH KOREA":"NON_US",
    "SPAIN":"NON_US","FINLAND":"NON_US","CANADA":"NON_US","AUSTRALIA":"NON_US","BERMUDA":"NON_US",
    "IRELAND":"NON_US","SWEDEN":"NON_US","NORWAY":"NON_US","DENMARK":"NON_US","BELGIUM":"NON_US",
    "LUXEMBOURG":"NON_US","HONG KONG":"NON_US","TAIWAN":"NON_US","SINGAPORE":"NON_US","BRAZIL":"NON_US",
    "MEXICO":"NON_US","CHINA":"NON_US","ISRAEL":"NON_US","INDIA":"NON_US","SOUTH AFRICA":"NON_US",
}
COUNTRY_RE = re.compile(r"^(" + "|".join(re.escape(x) for x in sorted(COUNTRY_NAMES, key=len, reverse=True)) + r")\s*(?:--|[-–—])?\s*(?:\d+(?:\.\d+)?\s*%)?\s*$", re.I)
CINS_NON_US = set("ABCDEFGHJKLMNPQRSTVWXYZ") - {"U"}


def fetch(url: str) -> str:
    last = None
    for candidate in ("https://r.jina.ai/" + url, url):
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read(5_000_000).decode("utf-8", "replace")
        except Exception as e:
            last = e
    raise RuntimeError(last)


def text_lines(raw: str) -> list[str]:
    lines=[]
    for line in raw.splitlines():
        s=re.sub(r"[*_`]+", "", line).strip()
        s=s.replace("\xa0", " ")
        s=re.sub(r"\s+", " ", s)
        if s: lines.append(s)
    return lines


def norm_desc(s: str) -> str:
    s=re.sub(r"\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$", "", s, flags=re.I)
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", s.upper()).split())


def source_sections(raw: str) -> list[tuple[str,str]]:
    state="UNKNOWN"
    out=[]
    for line in text_lines(raw):
        m=COUNTRY_RE.match(line.upper())
        if m:
            state=COUNTRY_NAMES[m.group(1).upper()]
            continue
        if re.search(r"\b(?:SHORT TERM INVESTMENTS|MONEY MARKET|NET ASSETS)\b", line, re.I):
            state="UNKNOWN"
        out.append((norm_desc(line),state))
    return out


def locate_country(desc: str, lines: list[tuple[str,str]]) -> str:
    q=norm_desc(desc)
    if not q: return "UNKNOWN"
    hits=[state for text,state in lines if q and q in text and state!="UNKNOWN"]
    return hits[0] if hits and all(x==hits[0] for x in hits) else "UNKNOWN"


def main() -> None:
    pit=json.loads(PIT.read_text())
    mapping=json.loads(MAPPING.read_text())
    by_key={(d.get("seriesId"),d.get("reportDate"),d.get("description")):d for d in mapping.get("details",[])}
    fetched={acc:source_sections(fetch(url)) for acc,url in SOURCES.items()}
    results=[]; counts=Counter(); weights=defaultdict(float); methods=Counter(); method_weights=defaultdict(float)
    for record in pit["records"]:
        lines=fetched.get(record.get("accession"),[])
        for h in record["holdings"]:
            desc=h["description"]; w=float(h.get("weight") or 0)
            country=locate_country(desc,lines) if lines else "UNKNOWN"
            method="NQ_EXPLICIT_COUNTRY_SECTION" if country!="UNKNOWN" else None
            d=by_key.get((record.get("seriesId"),record.get("reportDate"),desc))
            security_id=None; ticker=None
            if d and d.get("status")=="MATCHED_UNIQUE" and len(d.get("identities",[]))==1:
                ticker=d["identities"][0]["ticker"]; security_id=d["identities"][0]["securityId"]
            if country=="UNKNOWN" and security_id and len(security_id)==9 and security_id[0].isalpha() and security_id[0].upper() in CINS_NON_US:
                country="NON_US"; method="CINS_NON_US"
            counts[country]+=1; weights[country]+=w
            if method: methods[method]+=1; method_weights[method]+=w
            results.append({"seriesId":record.get("seriesId"),"seriesName":record.get("seriesName"),"fundTickers":record.get("fundTickers",[]),"reportDate":record.get("reportDate"),"description":desc,"weight":w,"ticker":ticker,"securityId":security_id,"classification":country,"method":method})
    total=len(results); total_w=sum(r["weight"] for r in results)
    out={"year":2006,"purpose":"Structural point-in-time US/NON_US attribution using only explicit legacy N-Q country sections and official CINS country-prefix semantics. No returns, rankings, current domicile, or listing venue used.","rules":["Explicit N-Q country heading is direct point-in-time evidence; UNITED STATES -> US, any other recognized country -> NON_US.","If no explicit N-Q country evidence and a uniquely mapped 9-character security ID is CINS (alphabetic first position), any non-U CINS prefix -> NON_US.","Numeric CUSIP is never treated as US because standard CUSIP also covers Canadian issuers; CINS U is not used as positive US proof in this diagnostic.","All remaining holdings stay UNKNOWN."],"holdingCount":total,"holdingWeight":total_w,"classificationCounts":dict(counts),"classificationWeights":dict(weights),"resolvedCountRate":(counts["US"]+counts["NON_US"])/total if total else None,"resolvedWeightRate":(weights["US"]+weights["NON_US"])/total_w if total_w else None,"methods":dict(methods),"methodWeights":dict(method_weights),"results":results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+"\n")
    print("SUMMARY",json.dumps({k:v for k,v in out.items() if k!="results"}),flush=True)
    for r in results:
        if r["classification"]!="UNKNOWN": print("RESOLVED",json.dumps(r),flush=True)

if __name__=="__main__":main()
