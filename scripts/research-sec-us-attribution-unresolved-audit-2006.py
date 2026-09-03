#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/research/sec-us-attribution-current-ticker-sample-2006.json"
OUT = ROOT / "data/research/sec-us-attribution-unresolved-audit-2006.json"
UA = {"User-Agent": "momentum-console research kensuke5704@users.noreply.github.com", "Accept": "text/plain,text/html,*/*"}
STATE_PATTERNS = [
    re.compile(r"State\s+of\s+Inc(?:orp(?:oration)?)?\.?\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?", re.I),
    re.compile(r"STATE-OF-INCORPORATION:\s*([A-Z0-9]{2,3})", re.I),
    re.compile(r"State or other jurisdiction of incorporation[^A-Z0-9]{0,80}([A-Z]{2})\b", re.I),
]
US_CODES = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"}


def get(url: str, timeout=12):
    last = None
    for u in ("https://r.jina.ai/" + url, url):
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(3_000_000).decode("utf-8", "replace"), u
        except Exception as e:
            last = repr(e)
    raise RuntimeError(last or "fetch failed")


def browse_cik(cik: str, dateb: str):
    q = urllib.parse.urlencode({"action":"getcompany","CIK":cik,"type":"10-K","dateb":dateb.replace('-',''),"owner":"exclude","count":"40"})
    text, transport = get("https://www.sec.gov/cgi-bin/browse-edgar?" + q)
    urls = list(dict.fromkeys(re.findall(r"https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"'<>\)]+", text, re.I)))
    return urls, transport


def find_state(text: str):
    for pat in STATE_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).upper(), pat.pattern
    return None, None


def main():
    data = json.loads(SAMPLE.read_text())
    unresolved = [r for r in data.get("results", []) if r.get("classification") == "UNKNOWN"]
    out_rows = []
    for row in unresolved:
        cik_candidates = []
        if row.get("seedCik"):
            cik_candidates.append(row["seedCik"])
        cik_candidates += row.get("ciks", [])
        if row.get("candidate", {}).get("cik"):
            cik_candidates.append(row["candidate"]["cik"])
        cik_candidates = list(dict.fromkeys(cik_candidates))
        audit = {"ticker": row["ticker"], "issuer": row["issuer"], "asOfReportDate": row["asOfReportDate"], "cikCandidates": cik_candidates, "attempts": []}
        for cik in cik_candidates:
            try:
                urls, transport = browse_cik(cik, row["asOfReportDate"])
                a = {"cik": cik, "browseTransport": transport, "archiveCount": len(urls)}
                for url in urls[:20]:
                    try:
                        text, t = get(url)
                        state, pattern = find_state(text)
                        if state:
                            a.update({"stateCode": state, "classification": "US" if state in US_CODES else "NON_US", "filingUrl": url, "filingTransport": t, "pattern": pattern})
                            break
                    except Exception as e:
                        a.setdefault("errors", []).append(type(e).__name__)
                audit["attempts"].append(a)
                if a.get("classification"):
                    audit.update({"classification": a["classification"], "stateCode": a["stateCode"], "resolvedCik": cik})
                    break
            except Exception as e:
                audit["attempts"].append({"cik": cik, "error": repr(e)})
        audit.setdefault("classification", "UNKNOWN")
        out_rows.append(audit)
        print("AUDIT", json.dumps(audit), flush=True)
    summary = {"purpose":"Audit only the four preregistered unresolved cases from the fixed 24-security sample using broader historical filing header patterns and 10-K-scoped PIT searches. No returns or universe ranks used.", "inputUnresolved":len(unresolved), "resolved":sum(r["classification"] != "UNKNOWN" for r in out_rows), "remainingUnknown":sum(r["classification"] == "UNKNOWN" for r in out_rows), "rows":out_rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k:v for k,v in summary.items() if k != "rows"}), flush=True)

if __name__ == "__main__":
    main()
# rerun marker: 2026-09-03 Gate B country bridge audit
