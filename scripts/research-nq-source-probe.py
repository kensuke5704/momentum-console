#!/usr/bin/env python3
import urllib.request

URLS=[
('sec-archives','https://www.sec.gov/Archives/edgar/data/853437/000085343707000010/ustfnq.htm'),
('secdatabase','https://edgar.secdatabase.com/1142/127512504000362/filing-main.htm'),
]
for name,url in URLS:
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/html'})
        with urllib.request.urlopen(req,timeout=60) as r:
            b=r.read(200000)
        print(name,'OK',len(b),b[:120].decode('utf-8','replace').replace('\n',' '))
    except Exception as e:
        print(name,'FAIL',repr(e))
