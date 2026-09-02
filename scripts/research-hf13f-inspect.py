#!/usr/bin/env python3
import json, urllib.request
REPO='kurry/institutional-holdings-13f-quarterly'
UA='momentum-console-research/1.0'

def get(url):
 r=urllib.request.Request(url,headers={'User-Agent':UA})
 with urllib.request.urlopen(r,timeout=60) as x:return json.load(x)

meta=get(f'https://huggingface.co/api/datasets/{REPO}')
print('META',json.dumps({k:meta.get(k) for k in ['id','lastModified','downloads','usedStorage']},ensure_ascii=False))
print('SIBLINGS')
for x in meta.get('siblings',[]):
 print(json.dumps(x,ensure_ascii=False))
try:
 tree=get(f'https://huggingface.co/api/datasets/{REPO}/tree/main?recursive=true&expand=true')
 print('TREE_COUNT',len(tree))
 for x in tree:
  print('TREE',json.dumps(x,ensure_ascii=False))
except Exception as e:
 print('TREE_ERROR',repr(e))
