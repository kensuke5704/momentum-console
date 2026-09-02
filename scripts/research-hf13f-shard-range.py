#!/usr/bin/env python3
import os, urllib.request
from pathlib import Path
import pyarrow as pa
import pyarrow.ipc as ipc
BASE='https://huggingface.co/datasets/kurry/institutional-holdings-13f-quarterly/resolve/main/holdings'
UA='momentum-console-research/1.0'
SHARDS=[10,11]
root=Path('/tmp/hf13f'); root.mkdir(exist_ok=True)
for i in SHARDS:
 name=f'data-{i:05d}-of-00012.arrow'; p=root/name
 if not p.exists():
  print('DOWNLOAD',name,flush=True)
  r=urllib.request.Request(f'{BASE}/{name}',headers={'User-Agent':UA})
  with urllib.request.urlopen(r,timeout=300) as src, open(p,'wb') as dst:
   while True:
    b=src.read(8*1024*1024)
    if not b:break
    dst.write(b)
 print('SIZE',name,p.stat().st_size,flush=True)
 with pa.memory_map(str(p),'r') as source:
  reader=ipc.open_stream(source)
  n=0; mn=None; mx=None; first=[]; last=[]
  for batch in reader:
   a=batch.column(batch.schema.get_field_index('fdate'))
   if len(a):
    lo=a[0].as_py(); hi=a[-1].as_py()
    mn=lo if mn is None or lo<mn else mn; mx=hi if mx is None or hi>mx else mx
    if len(first)<5:first.extend(a.slice(0,min(5-len(first),len(a))).to_pylist())
    last=a.slice(max(0,len(a)-5),min(5,len(a))).to_pylist()
   n+=batch.num_rows
 print('RANGE',name,'rows',n,'min',mn,'max',mx,'first',first,'last',last,flush=True)
 os.remove(p)
