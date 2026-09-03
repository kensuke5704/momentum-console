#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/gate-b-gfin-format-diagnostic-2020.json'
URL='https://www.sec.gov/Archives/edgar/data/1479026/000119312519276095/d774917dncsr.htm'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

def get():
    last=None
    for u in ('https://r.jina.ai/'+URL,URL):
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=40) as r:return r.read(12_000_000).decode('utf-8','replace'),u
        except Exception as e:last=repr(e)
    raise RuntimeError(last)

def main():
    text,tr=get();lines=text.splitlines();targets=[]
    pats=[r'Finance Reimagined',r'GFIN',r'Schedule of Investments',r'Portfolio of Investments',r'COMMON STOCK',r'COMMON STOCKS']
    for i,x in enumerate(lines):
        if any(re.search(p,x,re.I) for p in pats):targets.append(i)
    windows=[]
    # deterministic diagnostic: first 25 unique target hits + target-title neighborhoods.
    for i in list(dict.fromkeys(targets))[:40]:
        windows.append({'at':i,'lines':lines[max(0,i-12):min(len(lines),i+45)]})
    title_hits=[i for i,x in enumerate(lines) if re.search(r'Goldman Sachs (?:Motif )?Finance Reimagined ETF',x,re.I)]
    out={'transport':tr,'lineCount':len(lines),'targetHits':targets[:100],'titleHits':title_hits[:30],'windows':windows}
    print('SUMMARY',json.dumps({'lineCount':len(lines),'targetHits':targets[:100],'titleHits':title_hits[:30]}),flush=True)
    for w in windows:
        if w['at'] in title_hits or any(re.search(r'COMMON STOCK|Schedule of Investments|Portfolio of Investments',z,re.I) for z in w['lines']):print('WINDOW',json.dumps(w),flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
