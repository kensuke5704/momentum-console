#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/gate-b-ppty-netassets-diagnostic-2020.json'
URL='https://www.sec.gov/Archives/edgar/data/1540305/000119312519207140/d784474dnportex.htm'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

def get():
    last=None
    for u in ('https://r.jina.ai/'+URL,URL):
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=45) as r:return r.read(12_000_000).decode('utf-8','replace'),u
        except Exception as e:last=repr(e)
    raise RuntimeError(last)

def plain(s):return ' '.join(re.sub(r'[*_]+','',s or '').replace('\xa0',' ').split())

def main():
    text,tr=get();lines=text.splitlines();hits=[]
    for i,x in enumerate(lines):
        p=plain(x)
        if re.search(r'NET ASSETS|TOTAL COMMON STOCKS|TOTAL INVESTMENTS',p,re.I):
            hits.append({'at':i,'line':p,'before':[plain(y) for y in lines[max(0,i-6):i] if plain(y)],'after':[plain(y) for y in lines[i+1:min(len(lines),i+12)] if plain(y)]})
    print('PPTY_NET',json.dumps(hits),flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'transport':tr,'hits':hits},indent=2)+'\n')
if __name__=='__main__':main()
