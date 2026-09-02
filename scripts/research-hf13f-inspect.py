#!/usr/bin/env python3
import json, urllib.request
REPO='kurry/institutional-holdings-13f-quarterly'; UA='momentum-console-research/1.0'; BASE=f'https://huggingface.co/datasets/{REPO}/resolve/main'
def raw_json(path):
 r=urllib.request.Request(f'{BASE}/{path}',headers={'User-Agent':UA})
 with urllib.request.urlopen(r,timeout=60) as x:return json.load(x)
def api(url):
 r=urllib.request.Request(url,headers={'User-Agent':UA})
 with urllib.request.urlopen(r,timeout=60) as x:return json.load(x)
meta=api(f'https://huggingface.co/api/datasets/{REPO}')
print('META',json.dumps({k:meta.get(k) for k in ['id','lastModified','downloads','usedStorage']},ensure_ascii=False))
for p in ['holdings/state.json','holdings/dataset_info.json','state.json','dataset_info.json']:
 try: print(p,json.dumps(raw_json(p),ensure_ascii=False))
 except Exception as e: print(p,'ERROR',repr(e))
tree=api(f'https://huggingface.co/api/datasets/{REPO}/tree/main?recursive=true&expand=true')
for x in tree:
 if x.get('path','').startswith('holdings/'):
  print('TREE',json.dumps({k:x.get(k) for k in ['path','size','lfs','xetHash']},ensure_ascii=False))
