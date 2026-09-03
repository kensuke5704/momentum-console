#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/gate-b-gfin-source-and-ppty-audit-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

def get(url,prefer_direct=False):
    last=None
    order=(url,'https://r.jina.ai/'+url) if prefer_direct else ('https://r.jina.ai/'+url,url)
    for u in order:
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=40) as r:
                return r.read(16_000_000).decode('utf-8','replace'),u
        except Exception as e:last=repr(e)
    raise RuntimeError(last or 'fetch failed')

def main():
    out={}
    acc='0001193125-19-276095'
    base='https://www.sec.gov/Archives/edgar/data/1479026/000119312519276095/'
    index_url=base+'0001193125-19-276095-index.htm'
    try:
        text,tr=get(index_url)
        links=[]
        for m in re.finditer(r'https://www\.sec\.gov/Archives/edgar/data/1479026/000119312519276095/([^\s\)\]"<>]+)',text,re.I):
            name=m.group(1).rstrip('.,')
            if name not in links:links.append(name)
        for m in re.finditer(r'\b([a-zA-Z0-9_-]+\.(?:htm|html|txt))\b',text):
            name=m.group(1)
            if name not in links:links.append(name)
        out['gfinIndex']={'accession':acc,'indexUrl':index_url,'transport':tr,'documents':links[:80],'textHits':[line.strip() for line in text.splitlines() if 'N-CSR' in line or 'GOLDMAN SACHS ETF TRUST' in line][:20]}
        print('GFIN_INDEX',json.dumps(out['gfinIndex']),flush=True)
    except Exception as e:
        out['gfinIndex']={'accession':acc,'status':'ERROR','error':repr(e)};print('GFIN_INDEX',json.dumps(out['gfinIndex']),flush=True)

    complete=base+'0001193125-19-276095.txt'
    try:
        text,tr=get(complete,prefer_direct=True)
        docs=[]
        # Direct complete-submission preserves SGML. Capture type/filename and whether target series/title appears.
        for block in re.split(r'<DOCUMENT>',text,flags=re.I)[1:]:
            typ=(re.search(r'<TYPE>\s*([^\r\n<]+)',block,re.I) or [None,''])[1].strip()
            fn=(re.search(r'<FILENAME>\s*([^\r\n<]+)',block,re.I) or [None,''])[1].strip()
            desc=(re.search(r'<DESCRIPTION>\s*([^\r\n<]+)',block,re.I) or [None,''])[1].strip()
            hit=('S000063326' in block or 'Goldman Sachs Motif Finance Reimagined ETF' in block or 'GOLDMAN SACHS MOTIF FINANCE REIMAGINED ETF' in block)
            if fn or typ:docs.append({'type':typ,'filename':fn,'description':desc,'targetHit':hit})
        # If SGML was stripped by transport, still search rendered text for likely document names near N-CSR/title.
        rendered_names=[]
        for line in text.splitlines():
            if 'Finance Reimagined ETF' in line or 'N-CSR' in line:
                rendered_names.extend(re.findall(r'\b[a-zA-Z0-9_-]+\.(?:htm|html)\b',line))
        rendered_names=list(dict.fromkeys(rendered_names))
        out['gfinComplete']={'transport':tr,'sgmlDocuments':docs[:80],'targetDocuments':[d for d in docs if d['targetHit'] or d['type'].upper()=='N-CSR'],'renderedNames':rendered_names[:40],'containsTargetTitle':'Finance Reimagined ETF' in text}
        print('GFIN_COMPLETE',json.dumps(out['gfinComplete']),flush=True)
    except Exception as e:
        out['gfinComplete']={'status':'ERROR','error':repr(e)};print('GFIN_COMPLETE',json.dumps(out['gfinComplete']),flush=True)

    ppty='https://www.sec.gov/Archives/edgar/data/1540305/000119312519207140/d784474dnportex.htm'
    try:
        text,tr=get(ppty);lines=text.splitlines()
        start=next(i for i,x in enumerate(lines) if re.search(r'COMMON STOCKS\s*-\s*100\.0%',x,re.I))
        end=next(i for i in range(start+1,len(lines)) if re.search(r'TOTAL COMMON STOCKS',lines[i],re.I))
        seg=lines[start:end]
        issuers=[]
        for i,x in enumerate(seg):
            s=' '.join(x.replace('\xa0',' ').split())
            if not s or not re.search(r'[A-Za-z]',s):continue
            if re.search(r'COMMON STOCKS|Security Description|TOTAL|Percentages|Annualized|Cost \$',s,re.I):continue
            if re.search(r'\d+(?:\.\d+)?\s*%$',s):continue
            prev=' '.join(' '.join(z.replace('\xa0',' ').split()) for z in seg[max(0,i-4):i])
            foll=' '.join(' '.join(z.replace('\xa0',' ').split()) for z in seg[i+1:min(len(seg),i+5)])
            if re.search(r'\b\d[\d,]*\b',prev) and re.search(r'\b\d[\d,]*\b',foll):issuers.append(s)
        issuers=list(dict.fromkeys(issuers))
        out['pptySchedule']={'transport':tr,'startLine':start,'endLine':end,'issuerCountStructural':len(issuers),'sample':issuers[:30]}
        print('PPTY_SCHEDULE',json.dumps(out['pptySchedule']),flush=True)
    except Exception as e:
        out['pptySchedule']={'status':'ERROR','error':repr(e)};print('PPTY_SCHEDULE',json.dumps(out['pptySchedule']),flush=True)

    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
