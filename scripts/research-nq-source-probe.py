#!/usr/bin/env python3
import urllib.request

UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

def get(url,limit=3000000):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=90) as r:
        return getattr(r,'status',None),r.headers.get('content-type',''),r.read(limit)

TARGET='https://www.sec.gov/Archives/edgar/data/53808/0000053808-05-000021.txt'
INDEX='https://www.sec.gov/Archives/edgar/full-index/2005/QTR4/master.idx'
for name,url in [
    ('sec-archives', TARGET),
    ('jina-filing', 'https://r.jina.ai/'+TARGET),
    ('jina-master-index', 'https://r.jina.ai/'+INDEX),
]:
    try:
        status,ctype,b=get(url)
        text=b.decode('utf-8','replace')
        print(name,'OK','status=',status,'bytes=',len(b),'ctype=',ctype)
        if name=='jina-filing':
            print('markers',{'nq':('N-Q' in text or 'FORM N-Q' in text),'portfolio':('PORTFOLIO' in text.upper()),'holdings':('HOLDINGS' in text.upper())})
        if name=='jina-master-index':
            lines=[ln for ln in text.splitlines() if '|N-Q|' in ln or '|N-CSR|' in ln or '|N-CSRS|' in ln]
            print('target-form-lines',len(lines),'sample=',lines[:5])
        print(text[:250].replace('\n',' '))
    except Exception as e: print(name,'FAIL',repr(e))
