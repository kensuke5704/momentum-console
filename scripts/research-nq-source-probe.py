#!/usr/bin/env python3
import urllib.request

TARGET='https://www.sec.gov/Archives/edgar/data/53808/0000053808-05-000021.txt'
URLS=[
('sec-archives', TARGET),
('jina-reader', 'https://r.jina.ai/'+TARGET),
('secinfo-known', 'https://www.secinfo.com/d2wVq.k1qf.f.htm'),
]
for name,url in URLS:
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'})
        with urllib.request.urlopen(req,timeout=90) as r:
            b=r.read(1000000)
            status=getattr(r,'status',None)
            ctype=r.headers.get('content-type','')
        text=b.decode('utf-8','replace')
        markers={
            'nq': ('N-Q' in text or 'FORM N-Q' in text),
            'portfolio': ('PORTFOLIO' in text.upper()),
            'holdings': ('HOLDINGS' in text.upper()),
        }
        print(name,'OK','status=',status,'bytes=',len(b),'ctype=',ctype,'markers=',markers)
        print(text[:300].replace('\n',' '))
    except Exception as e:
        print(name,'FAIL',repr(e))
