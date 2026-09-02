#!/usr/bin/env python3
import json, urllib.parse, urllib.request

UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'application/json,text/plain,text/html,*/*'}

def get(url,limit=1000000):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=90) as r:
        return getattr(r,'status',None),r.headers.get('content-type',''),r.read(limit)

TARGET='https://www.sec.gov/Archives/edgar/data/53808/0000053808-05-000021.txt'
for name,url in [
    ('sec-archives', TARGET),
    ('jina-reader', 'https://r.jina.ai/'+TARGET),
    ('secinfo-known', 'https://www.secinfo.com/d2wVq.k1qf.f.htm'),
]:
    try:
        status,ctype,b=get(url)
        text=b.decode('utf-8','replace')
        markers={'nq':('N-Q' in text or 'FORM N-Q' in text),'portfolio':('PORTFOLIO' in text.upper()),'holdings':('HOLDINGS' in text.upper())}
        print(name,'OK','status=',status,'bytes=',len(b),'ctype=',ctype,'markers=',markers)
        print(text[:300].replace('\n',' '))
    except Exception as e: print(name,'FAIL',repr(e))

# Public Hugging Face dataset metadata / row server probe. This dataset is only
# used to enumerate EDGAR accession URLs; filing content remains SEC-origin via Jina.
for name,url in [
    ('hf-meta','https://huggingface.co/api/datasets/arthrod/SEC_filings_1994_2024'),
    ('hf-parquet','https://datasets-server.huggingface.co/parquet?dataset='+urllib.parse.quote('arthrod/SEC_filings_1994_2024',safe='')),
]:
    try:
        status,ctype,b=get(url,3000000)
        obj=json.loads(b)
        print(name,'OK','status=',status,'bytes=',len(b))
        if name=='hf-meta':
            print('siblings',[(x.get('rfilename'),x.get('size')) for x in obj.get('siblings',[])[:20]])
        else:
            print('parquet',obj)
    except Exception as e: print(name,'FAIL',repr(e))
