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

def get():
    last=None
    for u in ('https://r.jina.ai/'+URL,URL):
        try:
            req=urllib.request.Request(u,headers=UA)
            with urllib.request.urlopen(req,timeout=45) as r:return r.read(12_000_000).decode('utf-8','replace'),u
        except Exception as e:last=repr(e)
    raise RuntimeError(last)

def main():
    text,tr=get();lines=text.splitlines()
    title_hits=[i for i,x in enumerate(lines) if TITLE.search(x)]
    sched_hits=[i for i,x in enumerate(lines) if SCHED.search(x)]
    candidates=[]
    for t in title_hits:
        near=sorted(sched_hits,key=lambda s:abs(s-t))[:5]
        candidates.append({'titleAt':t,'nearestScheduleHits':near,'distances':[abs(s-t) for s in near]})
    # Print title windows and every schedule within 250 lines of a GFIN title.
    selected=[]
    for t in title_hits:
        selected.append(t)
        selected.extend(s for s in sched_hits if abs(s-t)<=250)
    selected=sorted(set(selected))
    windows=[{'at':i,'kind':'title' if i in title_hits else 'schedule','lines':lines[max(0,i-20):min(len(lines),i+90)]} for i in selected]
    out={'transport':tr,'lineCount':len(lines),'titleHits':title_hits,'scheduleHitsNearTitles':candidates,'windows':windows}
    print('SUMMARY',json.dumps({'lineCount':len(lines),'titleHits':title_hits,'scheduleHitsNearTitles':candidates}),flush=True)
    for w in windows:print('WINDOW',json.dumps(w),flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
