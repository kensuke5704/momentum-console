#!/usr/bin/env python3
from __future__ import annotations
import urllib.request

UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
URLS=[
 ('www-filing','https://www.sec.gov/Archives/edgar/data/909112/0000909112-06-000003.txt'),
 ('files-filing','https://files.sec.gov/Archives/edgar/data/909112/0000909112-06-000003.txt'),
 ('www-feed','https://www.sec.gov/Archives/edgar/Feed/2006/QTR1/20060103.nc.tar.gz'),
 ('files-feed-archives','https://files.sec.gov/Archives/edgar/Feed/2006/QTR1/20060103.nc.tar.gz'),
 ('files-feed','https://files.sec.gov/Feed/2006/QTR1/20060103.nc.tar.gz'),
 ('www-feed-index','https://www.sec.gov/Archives/edgar/Feed/2006/QTR1/index.json'),
 ('files-feed-index','https://files.sec.gov/Feed/2006/QTR1/index.json'),
 ('financialfilings','https://financialfilings.com/filings/new-germany-fund-inc/interim-quarterly-report/2006/9788470/'),
]
for name,url in URLS:
    try:
        req=urllib.request.Request(url,headers={**UA,'Range':'bytes=0-65535'})
        with urllib.request.urlopen(req,timeout=60) as r:
            b=r.read(65536)
            print(name,'OK','status=',r.status,'final=',r.geturl(),'bytes=',len(b),'ctype=',r.headers.get('content-type'),'range=',r.headers.get('content-range'),'magic=',repr(b[:12]),flush=True)
    except Exception as e:
        print(name,'FAIL',repr(e),flush=True)
