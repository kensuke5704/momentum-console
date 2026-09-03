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

def context(lines,i,a=10,b=24):
    return [{'at':j,'line':plain(lines[j])} for j in range(max(0,i-a),min(len(lines),i+b)) if plain(lines[j])]

def main():
    text,tr=get();lines=text.splitlines();title_hits=[i for i,x in enumerate(lines) if TITLE.search(x)];sched_hits=[i for i,x in enumerate(lines) if SCHED.search(x)]
    title_windows=[{'titleAt':t,'title':plain(lines[t]),'nearestSchedules':sorted(sched_hits,key=lambda s:abs(s-t))[:5],'context':context(lines,t)} for t in title_hits]
    print('TITLE_WINDOWS',json.dumps(title_windows),flush=True)
    candidates=[]
    for t in title_hits:
        for s in sched_hits:
            if 0 <= s-t <= 80:
                window='\n'.join(plain(x) for x in lines[s:min(len(lines),s+140)])
                if re.search(r'Common Stocks',window,re.I):
                    candidates.append({'titleAt':t,'scheduleAt':s,'distance':s-t,'title':plain(lines[t]),'schedule':plain(lines[s]),'sample':[plain(x) for x in lines[s:min(len(lines),s+40)] if plain(x)][:25]})
    print('CANDIDATES',json.dumps(candidates),flush=True)
    out={'transport':tr,'titleHits':title_hits,'scheduleHits':sched_hits,'titleWindows':title_windows,'candidates':candidates}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
