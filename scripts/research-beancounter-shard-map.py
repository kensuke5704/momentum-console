#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.parse, urllib.request, zlib

UA={'User-Agent':'momentum-console research','Accept':'application/json'}
API='https://huggingface.co/api/datasets/bradfordlevy/BeanCounter/tree/main/train?recursive=false&expand=false&limit=1000'
BASE='https://huggingface.co/datasets/bradfordlevy/BeanCounter/resolve/main/'

def get_json(url:str):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)

def first_json(path:str):
    url=BASE+urllib.parse.quote(path,safe='/')
    req=urllib.request.Request(url,headers={'User-Agent':'momentum-console research','Range':'bytes=0-4194303'})
    with urllib.request.urlopen(req,timeout=180) as r:
        data=r.read(4_194_304); status=getattr(r,'status',None); final=r.geturl()
    dec=zlib.decompressobj(16+zlib.MAX_WBITS)
    txt=dec.decompress(data).decode('utf-8','replace')
    lines=[x for x in txt.splitlines() if x.strip()]
    obj=json.loads(lines[0]) if lines else None
    return {'path':path,'status':status,'finalUrl':final,'rangeBytes':len(data),'first':obj}

def main():
    tree=get_json(API)
    files=[x for x in tree if x.get('type')=='file']
    print('train files=',len(files),flush=True)
    print('FIRST_NAMES',json.dumps([{k:x.get(k) for k in ('path','size','oid')} for x in files[:30]],indent=2),flush=True)
    if not files:return
    n=len(files)
    positions=sorted(set([0,n//10,n//5,3*n//10,2*n//5,n//2,3*n//5,7*n//10,4*n//5,9*n//10,n-1]))
    results=[]
    for pos in positions:
        x=files[pos]
        try:
            r=first_json(x['path']); results.append(r); o=r['first'] or {}
            print(pos,x['path'],'date=',o.get('date'),'type=',o.get('type_filing'),'ts=',o.get('ts_accept'),'accession=',o.get('accession'),flush=True)
        except Exception as e: print(pos,x['path'],'FAIL',repr(e),flush=True)
    print('RESULT',json.dumps(results)[:30000])

if __name__=='__main__':main()
