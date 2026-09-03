#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
S=importlib.util.spec_from_file_location('sg',ROOT/'scripts'/'research-transition-shortgap-fidelity-2019.py')
sg=importlib.util.module_from_spec(S);S.loader.exec_module(sg);n=sg.nearest
TARGETS={k:v for k,v in sg.nearest.CHOSEN.items() if v[3]=='2019-09-30' and k in {'S000038223','S000047480','S000050191','S000053021','S000053022'}}

def first(filings):
 d={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in d:d[sid]=f
 return d

def parse_all_common(seg):
 rows=[];inside=False;lines=seg.splitlines();i=0
 while i<len(lines):
  raw=lines[i];line=n.clean(raw)
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):inside=True;i+=1;continue
  if inside and n.STOP_RE.search(line):inside=False;i+=1;continue
  if not inside:i+=1;continue
  cells=[n.clean(c) for c in re.split(r'\t+',raw) if n.clean(c) not in {'','$','—','-'}]
  nums=[(k,n.num(c)) for k,c in enumerate(cells) if n.NUM_RE.match(c)]
  if len(nums)>=2 and nums[0][0]>0:
   desc=' '.join(cells[:nums[0][0]]).strip();value=nums[-1][1]
   if desc and value is not None and not desc.lower().startswith('total '):rows.append({'raw':desc,'base':base_name(desc)})
   i+=1;continue
  if len(nums)==1 and nums[0][0]>0 and i+1<len(lines):
   nxt=[n.clean(c) for c in re.split(r'\t+',lines[i+1]) if n.clean(c) not in {'','$','—','-'}]
   if any(n.NUM_RE.match(c) for c in nxt):
    desc=' '.join(cells[:nums[0][0]]).strip()
    if desc and not desc.lower().startswith('total '):rows.append({'raw':desc,'base':base_name(desc)});i+=2;continue
  i+=1
 # issuer-name dedupe only for source-retention test
 seen=set();out=[]
 for r in rows:
  if r['base'] and r['base'] not in seen:seen.add(r['base']);out.append(r)
 return out

def base_name(s):
 x=n.norm(s)
 # SEC shareholder reports commonly append share-class labels that N-PORT issuerName omits.
 x=re.sub(r'\bCLASS\s+[A-Z0-9]+\b',' ',x)
 return ' '.join(x.split())

def unique_equiv(target,legacy_bases):
 t=base_name(target)
 exact=[x for x in legacy_bases if x==t]
 if len(exact)==1:return exact[0],'exact'
 # N-PORT issuerName is visibly field-truncated in the source (e.g. "Science Applications Internati").
 # Allow only deterministic unique prefix reconciliation, minimum 20 characters; no edit-distance/fuzzy match.
 cand=[]
 for x in legacy_bases:
  short,long=(t,x) if len(t)<=len(x) else (x,t)
  if len(short)>=20 and long.startswith(short):cand.append(x)
 return (cand[0],'unique_prefix') if len(cand)==1 else (None,None)

with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
filings=b.get('snapshots',b) if isinstance(b,dict) else b;fs=first(filings)
names={sid:(fs[sid].get('seriesName') or fs[sid].get('fundName') or '') for sid in TARGETS}
for sid,(cik,acc,form,rd) in TARGETS.items():
 name=names[sid];du=n.docs(cik,acc,form);hits=[]
 for u in du:
  hit=n.locate_doc([u],name)
  if hit and n.structural_start(hit[3].splitlines(),name) is not None:hits.append(hit)
 hit=sorted(hits,key=lambda x:(x[0],x[1]),reverse=True)[0]
 same=[names[x] for x,v in TARGETS.items() if v[:3]==(cik,acc,form)]
 seg=n.slice_series(hit[3],name,same);legacy=parse_all_common(seg);lb=[r['base'] for r in legacy]
 ph=[h for h in fs[sid].get('holdings',[]) if h.get('issuerName')]
 matched=[];unmatched=[]
 for h in ph:
  m,method=unique_equiv(h['issuerName'],lb)
  (matched if m else unmatched).append({'nportIssuer':h['issuerName'],'symbol':h.get('symbol'),'legacyBase':m,'method':method})
 rec={'seriesId':sid,'seriesName':name,'days':( __import__('datetime').date.fromisoformat(fs[sid]['reportDate'])-__import__('datetime').date.fromisoformat(rd)).days,'legacyCommonStocks':len(legacy),'nportFilteredHoldings':len(ph),'nportRetained':len(matched),'nportRetentionRate':len(matched)/len(ph) if ph else None,'unmatchedNport':unmatched}
 print('RETENTION',json.dumps(rec),flush=True)
