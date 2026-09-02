#!/usr/bin/env python3
import urllib.request

UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}

def get(url,limit=3000000):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=120) as r:
        return getattr(r,'status',None),r.headers.get('content-type',''),r.headers.get('content-length'),r.read(limit)

TARGET='https://www.sec.gov/Archives/edgar/data/53808/0000053808-05-000021.txt'
DRIVE='https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
for name,url,limit in [
    ('sec-archives', TARGET,1000000),
    ('jina-filing', 'https://r.jina.ai/'+TARGET,1000000),
    ('nd-master-index-zip',DRIVE,128),
]:
    try:
        status,ctype,clen,b=get(url,limit)
        print(name,'OK','status=',status,'bytes-read=',len(b),'content-length=',clen,'ctype=',ctype,'prefix=',repr(b[:32]))
        if name=='jina-filing':
            text=b.decode('utf-8','replace');print('markers',{'nq':('N-Q' in text or 'FORM N-Q' in text),'portfolio':('PORTFOLIO' in text.upper()),'holdings':('HOLDINGS' in text.upper())})
        if name=='nd-master-index-zip': print('zipMagic=',b[:4]==b'PK\x03\x04')
    except Exception as e: print(name,'FAIL',repr(e))
