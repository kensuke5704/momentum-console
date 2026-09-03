#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/gate-b-gfin-format-diagnostic-2020.json'
URL='https://www.sec.gov/Archives/edgar/data/1479026/000119312519276095/d774917dncsr.htm'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
TITLE=re.compile(r'Goldman Sachs (?:Motif )?Finance Reimagined ETF',re.I)
SCHED=re.compile(r'Schedule of Investments|Portfolio of Investments',re.I)
KEY=re.compile(r'Common Stocks|Repurchase Agreements|Total Investments|Net Assets',re.I)

def get():
    last=None
    for u in ('https://r.jina.ai/'+URL,URL):
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=45) as r:return r.read(12_000_000).decode('utf-8','replace'),u
        except Exception as e:last=repr(e)
    raise RuntimeError(last)

def plain(s): return ' '.join(re.sub(r'[*_]+','',s or '').replace('\xa0',' ').split())

def main():
    text,tr=get();lines=text.splitlines();title_hits=[i for i,x in enumerate(lines) if TITLE.search(x)];sched_hits=[i for i,x in enumerate(lines) if SCHED.search(x)]
    starts=[]
    for t in title_hits:
        near=[s for s in sched_hits if abs(s-t)<=30]
        if near: starts.append(min([t]+near))
    start=min(starts) if starts else (title_hits[0] if title_hits else 0)
    # Stop before the next Goldman Sachs ETF title after the target schedule.
    end=min(len(lines),start+700)
    for i in range(start+30,end):
        p=plain(lines[i])
        if re.match(r'^Goldman Sachs .* ETF$',p,re.I) and not TITLE.search(p):
            end=i;break
    key=[]
    for i in range(start,end):
        p=plain(lines[i])
        if KEY.search(p):
            key.append({'at':i,'line':p,'next':[plain(x) for x in lines[i+1:min(end,i+8)] if plain(x)]})
    out={'transport':tr,'start':start,'end':end,'keyLines':key}
    print('KEYLINES',json.dumps(key),flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
