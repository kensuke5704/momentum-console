#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAN=ROOT/'data/research/gate-b-production-source-manifest-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

def get(url):
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=30) as r:return r.read(8_000_000).decode('utf-8','replace'),u
  except Exception:pass
 raise RuntimeError('fetch failed')

def main():
 man=json.loads(MAN.read_text())
 for s in man['sources']:
  if s.get('status')!='VERIFIED_COMPLETE_HOLDINGS':continue
  text,tr=get(s['sourceDocumentUrl']);lines=text.splitlines()
  print('SOURCE',json.dumps({'seriesId':s['seriesId'],'transport':tr,'lineCount':len(lines)}),flush=True)
  hits=[i for i,x in enumerate(lines) if re.search(r'COMMON STOCKS?|SCHEDULE OF INVESTMENTS|SHORT[- ]TERM',x,re.I)]
  print('HITS',json.dumps(hits[:30]),flush=True)
  for h in hits[:8]:
   print('WINDOW',json.dumps({'at':h,'lines':lines[max(0,h-5):min(len(lines),h+35)]}),flush=True)
if __name__=='__main__':main()
