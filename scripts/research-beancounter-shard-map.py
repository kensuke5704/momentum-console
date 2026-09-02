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
    req=urllib.request.Request(url,headers={'User-Agent':'momentum-console research','Range':'bytes=0-1048575'})
    with urllib.request.urlopen(req,timeout=180) as r:data=r.read(1_048_576)
    dec=zlib.decompressobj(16+zlib.MAX_WBITS)
    txt=dec.decompress(data).decode('utf-8','replace')
    lines=[x for x in txt.splitlines() if x.strip()]
    return json.loads(lines[0]) if lines else None

def main():
    tree=get_json(API); files=[x for x in tree if x.get('type')=='file']
    print('train files=',len(files),flush=True)
    results=[]
    for shard in range(140,171):
        path=f'train/bc-{shard:03d}-of-512.jsonl.gz'
        try:
            o=first_json(path) or {}; row={'shard':shard,'path':path,'date':o.get('date'),'ts_accept':o.get('ts_accept'),'type_filing':o.get('type_filing'),'accession':o.get('accession')}; results.append(row)
            print(shard,row['date'],row['ts_accept'],row['type_filing'],row['accession'],flush=True)
        except Exception as e: print(shard,'FAIL',repr(e),flush=True)
    dates=[r for r in results if r['date']]
    year2006=[r for r in dates if str(r['date']).startswith('2006-')]
    if year2006:
        first=min(r['shard'] for r in year2006); last=max(r['shard'] for r in year2006)
        # include predecessor because a shard whose first row is 2005 may end in 2006; exclude successor only after confirming its first date >= 2007.
        print('CANDIDATE_2006_SHARDS',list(range(max(1,first-1),last+1)),flush=True)
    print('RESULT',json.dumps(results))

if __name__=='__main__':main()
