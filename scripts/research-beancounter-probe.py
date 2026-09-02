#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.parse, urllib.request

UA={'User-Agent':'momentum-console research','Accept':'application/json'}
BASE='https://huggingface.co'
DS='bradfordlevy/BeanCounter'

def get_json(url:str):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)

def main():
    urls=[
      f'{BASE}/api/datasets/{DS}',
      f'{BASE}/api/datasets/{DS}/tree/main?recursive=false&expand=false',
      f'https://huggingface.co/api/datasets/{DS}/parquet/default/train',
      'https://datasets-server.huggingface.co/parquet?dataset='+urllib.parse.quote(DS,safe=''),
    ]
    for u in urls:
        try:
            x=get_json(u)
            print('\nURL',u)
            if isinstance(x,list): print(json.dumps(x[:20],indent=2)[:12000])
            else: print(json.dumps(x,indent=2)[:12000])
        except Exception as e: print('\nFAIL',u,repr(e))

if __name__=='__main__':main()
