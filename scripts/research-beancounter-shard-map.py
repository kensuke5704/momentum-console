#!/usr/bin/env python3
from __future__ import annotations
import gzip, io, json, urllib.request, zlib

UA={'User-Agent':'momentum-console research','Accept':'application/octet-stream'}
BASE='https://huggingface.co/datasets/bradfordlevy/BeanCounter/resolve/main/train'
PROBES=[1,20,40,60,80,100,120,140,160,180,200,220]

def first_json(idx:int):
    name=f'bc-{idx:03d}-of-220.jsonl.gz'
    url=f'{BASE}/{name}'
    req=urllib.request.Request(url,headers={**UA,'Range':'bytes=0-2097151'})
    with urllib.request.urlopen(req,timeout=120) as r:
        data=r.read(2_097_152); status=getattr(r,'status',None); final=r.geturl()
    dec=zlib.decompressobj(16+zlib.MAX_WBITS)
    txt=dec.decompress(data).decode('utf-8','replace')
    lines=[x for x in txt.splitlines() if x.strip()]
    obj=json.loads(lines[0]) if lines else None
    return {'idx':idx,'name':name,'status':status,'finalUrl':final,'rangeBytes':len(data),'first':obj}

def main():
    out=[]
    for i in PROBES:
        try:
            r=first_json(i); out.append(r)
            x=r['first'] or {}
            print(i,'date=',x.get('date'),'type=',x.get('type_filing'),'accession=',x.get('accession'),'bytes=',r['rangeBytes'],flush=True)
        except Exception as e: print(i,'FAIL',repr(e),flush=True)
    print('RESULT',json.dumps(out)[:20000])

if __name__=='__main__':main()
