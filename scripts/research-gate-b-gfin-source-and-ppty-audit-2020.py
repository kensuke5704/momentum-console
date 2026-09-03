#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/gate-b-gfin-source-and-ppty-audit-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

def get(url):
    last=None
    for u in ('https://r.jina.ai/'+url,url):
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=40) as r:
                return r.read(12_000_000).decode('utf-8','replace'),u
        except Exception as e:last=repr(e)
    raise RuntimeError(last or 'fetch failed')

def main():
    out={}
    # Source was fixed independently from the later 2020 N-14 incorporation-by-reference statement.
    acc='0001193125-19-276095'
    base='https://www.sec.gov/Archives/edgar/data/1479026/000119312519276095/'
    index_url=base+'0001193125-19-276095-index.htm'
    try:
        text,tr=get(index_url)
        links=[]
        for m in re.finditer(r'https://www\.sec\.gov/Archives/edgar/data/1479026/000119312519276095/([^\s\)\]"<>]+)',text,re.I):
            name=m.group(1).rstrip('.,')
            if name not in links:links.append(name)
        # Also capture href-like relative document names from rendered index.
        for m in re.finditer(r'\b([a-zA-Z0-9_-]+\.(?:htm|html|txt))\b',text):
            name=m.group(1)
            if name not in links:links.append(name)
        out['gfinIndex']={'accession':acc,'indexUrl':index_url,'transport':tr,'documents':links[:80],'textHits':[line.strip() for line in text.splitlines() if 'N-CSR' in line or 'GOLDMAN SACHS ETF TRUST' in line][:20]}
        print('GFIN_INDEX',json.dumps(out['gfinIndex']),flush=True)
    except Exception as e:
        out['gfinIndex']={'accession':acc,'status':'ERROR','error':repr(e)};print('GFIN_INDEX',json.dumps(out['gfinIndex']),flush=True)

    ppty='https://www.sec.gov/Archives/edgar/data/1540305/000119312519207140/d784474dnportex.htm'
    try:
        text,tr=get(ppty);lines=text.splitlines()
        # Exact schedule is the first PPTY schedule. Count textual issuer cells between COMMON STOCKS and TOTAL COMMON STOCKS.
        start=next(i for i,x in enumerate(lines) if re.search(r'COMMON STOCKS\s*-\s*100\.0%',x,re.I))
        end=next(i for i in range(start+1,len(lines)) if re.search(r'TOTAL COMMON STOCKS',lines[i],re.I))
        seg=lines[start:end]
        issuers=[]
        for i,x in enumerate(seg):
            s=' '.join(x.replace('\xa0',' ').split())
            if not s or not re.search(r'[A-Za-z]',s):continue
            if re.search(r'COMMON STOCKS|Security Description|Hotels, Resorts|REIT|Real Estate|TOTAL|Percentages|Annualized|Cost \$',s,re.I):continue
            # A holding description in this rendering has a nearby prior shares integer and nearby following value integer.
            prev=' '.join(' '.join(z.replace('\xa0',' ').split()) for z in seg[max(0,i-4):i])
            foll=' '.join(' '.join(z.replace('\xa0',' ').split()) for z in seg[i+1:min(len(seg),i+5)])
            if re.search(r'\b\d[\d,]*\b',prev) and re.search(r'\b\d[\d,]*\b',foll):
                issuers.append(s)
        # preserve order, unique
        issuers=list(dict.fromkeys(issuers))
        out['pptySchedule']={'transport':tr,'startLine':start,'endLine':end,'issuerCountStructural':len(issuers),'sample':issuers[:30]}
        print('PPTY_SCHEDULE',json.dumps(out['pptySchedule']),flush=True)
    except Exception as e:
        out['pptySchedule']={'status':'ERROR','error':repr(e)};print('PPTY_SCHEDULE',json.dumps(out['pptySchedule']),flush=True)

    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
