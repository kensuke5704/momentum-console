#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
F=importlib.util.spec_from_file_location('fw',ROOT/'scripts'/'research-transition-nearest-fidelity-fixedwidth-2019.py')
fw=importlib.util.module_from_spec(F);F.loader.exec_module(fw);nf=fw.nf
D=importlib.util.spec_from_file_location('disc',ROOT/'scripts'/'research-transition-legacy-nearest-2019.py')
disc=importlib.util.module_from_spec(D);D.loader.exec_module(disc)
nf.OUT=ROOT/'data/research/firsttrust-fixedwidth-allseries-2019.json'
SCHED=re.compile(r'^\s*(?:PORTFOLIO|SCHEDULE) OF INVESTMENTS(?:\s*\(CONTINUED\))?\s*$',re.I)
COMMON=re.compile(r'\bCOMMON STOCKS?\b',re.I)
TARGETS=['S000010977','S000017177','S000017178','S000033237','S000050385']
with gzip.open(nf.BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
filings=b.get('snapshots',b) if isinstance(b,dict) else b;first=nf.earliest_nport(filings)

def all_names(cik,acc):
 info=disc.header(cik,acc);out=[]
 for sid in info.get('seriesIds',[]):
  f=first.get(sid)
  if f:
   name=f.get('seriesName') or f.get('fundName') or ''
   if name:out.append(name)
 return list(dict.fromkeys(out))

def slice_all(text,name,names):
 ls=text.splitlines();c=[]
 for i,x in enumerate(ls):
  if name.lower() not in x.lower():continue
  for j in range(i,min(len(ls),i+20)):
   if not SCHED.match(ls[j]):continue
   ca=next((k for k in range(j,min(len(ls),j+30)) if COMMON.search(ls[k])),None)
   if ca is not None:c.append((j-i,j,i))
 if not c:return ''
 _,sched,title=sorted(c,key=lambda x:(x[0],-x[1]))[0]
 end=len(ls)
 for p in range(sched+1,len(ls)):
  for other in names:
   if other==name or other.lower() not in ls[p].lower():continue
   if any(SCHED.match(ls[q]) and any(COMMON.search(ls[k]) for k in range(q,min(len(ls),q+30))) for q in range(p,min(len(ls),p+20))):
    end=p;break
  if end==p:break
 # If there is no next registered portfolio, stop at explicit final portfolio total/notes boundary.
 if end==len(ls):
  for p in range(sched+1,min(len(ls),sched+1800)):
   if re.search(r'^\s*(?:NOTES TO|STATEMENT OF ASSETS|See Notes to Schedule)',ls[p],re.I):end=p;break
 return '\n'.join(ls[max(0,title-2):end])

_old_loc=nf.slice_series
def slicer(text,name,ignored):
 # infer current accession group by trying known target CHOSEN records whose exact name matches
 sid=next((s for s in TARGETS if (first[s].get('seriesName') or first[s].get('fundName') or '')==name),None)
 if not sid:return _old_loc(text,name,ignored)
 cik,acc,form,rd=nf.CHOSEN[sid]
 return slice_all(text,name,all_names(cik,acc))
nf.slice_series=slicer
old=nf.parse_rows
def parse_rows(seg):
 r=fw.parse_fixed_width_inline(seg)
 candidates=[('fixed_width_allseries',r),old(seg)]
 plausible=[x for x in candidates if 5<=len(x[1])<=150]
 if plausible:return max(plausible,key=lambda x:len(x[1]))
 return max(candidates,key=lambda x:len(x[1]))
nf.parse_rows=parse_rows
nf.main()
