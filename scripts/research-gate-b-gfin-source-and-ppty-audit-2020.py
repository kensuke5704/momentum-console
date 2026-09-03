#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/gate-b-gfin-source-and-ppty-audit-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

def get(url,prefer_direct=False,range_bytes=None):
    last=None
    order=(url,'https://r.jina.ai/'+url) if prefer_direct else ('https://r.jina.ai/'+url,url)
    for u in order:
        try:
            headers=dict(UA)
            if range_bytes and not u.startswith('https://r.jina.ai/'):headers['Range']=f'bytes=0-{range_bytes-1}'
            req=urllib.request.Request(u,headers=headers)
            with urllib.request.urlopen(req,timeout=25) as r:
                return r.read(range_bytes or 12_000_000).decode('utf-8','replace'),u,getattr(r,'status',None),dict(r.headers)
        except Exception as e:last=repr(e)
    raise RuntimeError(last or 'fetch failed')

def parse_docs(text):
    docs=[]
    for block in re.split(r'<DOCUMENT>',text,flags=re.I)[1:]:
        def val(tag):
            m=re.search(rf'<{tag}>\s*([^\r\n<]+)',block,re.I);return m.group(1).strip() if m else ''
        typ,fn,desc=val('TYPE'),val('FILENAME'),val('DESCRIPTION')
        if fn or typ:docs.append({'type':typ,'filename':fn,'description':desc,'targetHit':('S000063326' in block or 'Finance Reimagined ETF' in block)})
    return docs

def main():
    out={};acc='0001193125-19-276095';base='https://www.sec.gov/Archives/edgar/data/1479026/000119312519276095/'
    index_url=base+'0001193125-19-276095-index.htm'
    try:
        text,tr,status,h=get(index_url);links=list(dict.fromkeys(re.findall(r'\b[a-zA-Z0-9_-]+\.(?:htm|html|txt)\b',text)))
        out['gfinIndex']={'accession':acc,'transport':tr,'documents':links[:80]};print('GFIN_INDEX',json.dumps(out['gfinIndex']),flush=True)
    except Exception as e:out['gfinIndex']={'status':'ERROR','error':repr(e)};print('GFIN_INDEX',json.dumps(out['gfinIndex']),flush=True)

    complete=base+'0001193125-19-276095.txt'
    attempts=[];docs=[]
    for n in (262144,524288,1048576):
        try:
            text,tr,status,h=get(complete,prefer_direct=True,range_bytes=n);d=parse_docs(text);attempts.append({'bytes':n,'transport':tr,'status':status,'contentRange':h.get('Content-Range'),'length':len(text),'docCount':len(d)})
            docs=d
            if any(x['type'].upper().startswith('N-CSR') and x['filename'] for x in d):break
        except Exception as e:attempts.append({'bytes':n,'status':'ERROR','error':repr(e)})
    ncsr=[d for d in docs if d['type'].upper().startswith('N-CSR')]
    out['gfinPrefix']={'attempts':attempts,'documents':docs[:40],'ncsrDocuments':ncsr[:10]};print('GFIN_PREFIX',json.dumps(out['gfinPrefix']),flush=True)

    # Small SEC index-headers document is another metadata-only fallback.
    headers_url=base+'0001193125-19-276095-index-headers.html'
    try:
        text,tr,status,h=get(headers_url);names=list(dict.fromkeys(re.findall(r'\b[a-zA-Z0-9_-]+\.(?:htm|html)\b',text)));hits=[x.strip() for x in text.splitlines() if 'N-CSR' in x or 'FILENAME' in x or 'Finance Reimagined' in x]
        out['gfinIndexHeaders']={'transport':tr,'names':names[:60],'hits':hits[:40]};print('GFIN_HEADERS',json.dumps(out['gfinIndexHeaders']),flush=True)
    except Exception as e:out['gfinIndexHeaders']={'status':'ERROR','error':repr(e)};print('GFIN_HEADERS',json.dumps(out['gfinIndexHeaders']),flush=True)

    ppty='https://www.sec.gov/Archives/edgar/data/1540305/000119312519207140/d784474dnportex.htm'
    try:
        text,tr,status,h=get(ppty);lines=text.splitlines();start=next(i for i,x in enumerate(lines) if re.search(r'COMMON STOCKS\s*-\s*100\.0%',x,re.I));end=next(i for i in range(start+1,len(lines)) if re.search(r'TOTAL COMMON STOCKS',lines[i],re.I));seg=lines[start:end];issuers=[]
        for i,x in enumerate(seg):
            s=' '.join(x.replace('\xa0',' ').split())
            if not s or not re.search(r'[A-Za-z]',s) or re.search(r'COMMON STOCKS|Security Description|TOTAL|Percentages|Annualized|Cost \$',s,re.I) or re.search(r'\d+(?:\.\d+)?\s*%$',s):continue
            prev=' '.join(' '.join(z.replace('\xa0',' ').split()) for z in seg[max(0,i-4):i]);foll=' '.join(' '.join(z.replace('\xa0',' ').split()) for z in seg[i+1:min(len(seg),i+5)])
            if re.search(r'\b\d[\d,]*\b',prev) and re.search(r'\b\d[\d,]*\b',foll):issuers.append(s)
        issuers=list(dict.fromkeys(issuers));out['pptySchedule']={'issuerCountStructural':len(issuers),'sample':issuers[:20]};print('PPTY_SCHEDULE',json.dumps(out['pptySchedule']),flush=True)
    except Exception as e:out['pptySchedule']={'status':'ERROR','error':repr(e)};print('PPTY_SCHEDULE',json.dumps(out['pptySchedule']),flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
