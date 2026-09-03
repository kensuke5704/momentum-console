#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json,re
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'data/sec-nport/bootstrap.json.gz';OUT=ROOT/'data/research/transition-source-retention-structural-2019.json'
S=importlib.util.spec_from_file_location('sg',ROOT/'scripts'/'research-transition-shortgap-fidelity-2019.py')
sg=importlib.util.module_from_spec(S);S.loader.exec_module(sg);n=sg.nearest
TARGETS=dict(sg.nearest.CHOSEN)
EXACT_SCHED=re.compile(r'^\s*(?:PORTFOLIO|SCHEDULE) OF INVESTMENTS(?:\s*\(CONTINUED\))?\s*$',re.I)
COMMON=re.compile(r'\bCOMMON STOCKS?\b',re.I)

def first(filings):
 d={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in d:d[sid]=f
 return d

def structural_slice(text,name,all_names):
 ls=text.splitlines();c=[]
 for i,x in enumerate(ls):
  if name.lower() not in x.lower():continue
  for j in range(i,min(len(ls),i+220)):
   if not EXACT_SCHED.match(ls[j]):continue
   ca=next((k for k in range(j,min(len(ls),j+300)) if COMMON.search(ls[k])),None)
   if ca is not None:c.append((j-i,j,ca,i))
 if not c:return ''
 # nearest real schedule following exact title; later wins ties to avoid TOC/front matter.
 _,sched,ca,title=sorted(c,key=lambda x:(x[0],-x[1]))[0]
 end=min(len(ls),sched+1800)
 for p in range(sched+1,end):
  for other in all_names:
   if other==name or other.lower() not in ls[p].lower():continue
   if any(EXACT_SCHED.match(ls[q]) for q in range(p,min(len(ls),p+220))):end=p;break
  if end==p:break
 return '\n'.join(ls[max(0,title-2):end])

def base_name(s):
 x=n.norm(s);x=re.sub(r'\bCLASS\s+[A-Z0-9]+\b',' ',x);return ' '.join(x.split())
def parse_all_common(seg):
 rows=[];inside=False
 for raw in seg.splitlines():
  line=n.clean(raw)
  if COMMON.search(line):inside=True;continue
  if inside and n.STOP_RE.search(line):inside=False;continue
  if not inside:continue
  cells=[n.clean(c) for c in re.split(r'\t+',raw) if n.clean(c) not in {'','$','—','-'}]
  nums=[(k,n.num(c)) for k,c in enumerate(cells) if n.NUM_RE.match(c)]
  if len(nums)>=2 and nums[0][0]>0:
   desc=' '.join(cells[:nums[0][0]]).strip()
   if desc and not desc.lower().startswith('total '):rows.append({'raw':desc,'base':base_name(desc)})
 seen=set();out=[]
 for r in rows:
  if r['base'] and r['base'] not in seen:seen.add(r['base']);out.append(r)
 return out

def unique_equiv(target,legacy_bases):
 t=base_name(target)
 if t in legacy_bases:return t,'exact'
 cand=[]
 for x in legacy_bases:
  short,long=(t,x) if len(t)<=len(x) else (x,t)
  if len(short)>=20 and long.startswith(short):cand.append(x)
 return (cand[0],'unique_prefix') if len(cand)==1 else (None,None)

with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
filings=b.get('snapshots',b) if isinstance(b,dict) else b;fs=first(filings)
names={sid:(fs[sid].get('seriesName') or fs[sid].get('fundName') or '') for sid in TARGETS if sid in fs}
rows=[]
for sid,(cik,acc,form,rd) in TARGETS.items():
 if sid not in names:continue
 name=names[sid];du=n.docs(cik,acc,form);hit=n.locate_doc(du,name)
 if not hit:continue
 same=[names[x] for x,v in TARGETS.items() if x in names and v[:3]==(cik,acc,form)]
 seg=structural_slice(hit[3],name,same);legacy=parse_all_common(seg);lb=[x['base'] for x in legacy]
 ph=[h for h in fs[sid].get('holdings',[]) if h.get('issuerName')]
 matched=[];unmatched=[]
 for h in ph:
  m,method=unique_equiv(h['issuerName'],lb);rec={'nportIssuer':h['issuerName'],'symbol':h.get('symbol'),'legacyBase':m,'method':method}
  (matched if m else unmatched).append(rec)
 r={'seriesId':sid,'seriesName':name,'days':(date.fromisoformat(fs[sid]['reportDate'])-date.fromisoformat(rd)).days,'segmentLines':len(seg.splitlines()),'legacyCommonStocks':len(legacy),'nportFilteredHoldings':len(ph),'nportRetained':len(matched),'nportRetentionRate':len(matched)/len(ph) if ph else None,'unmatchedNport':unmatched}
 rows.append(r);print('RETENTION',json.dumps(r),flush=True)
valid=[r for r in rows if r['legacyCommonStocks']>=10 and r['nportFilteredHoldings']]
out={'purpose':'Short-gap legacy source-retention from structurally anchored real schedules for all eight preregistered ETFMG series. Source extraction uses all explicit COMMON STOCKS; US/CORP attribution remains a separate gate. No returns or universe ranks used.','rows':rows,'validSeries':len(valid),'medianRetention':__import__('statistics').median([r['nportRetentionRate'] for r in valid]) if valid else None,'minimumRetention':min([r['nportRetentionRate'] for r in valid]) if valid else None}
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
