#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json,re,statistics
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'data/sec-nport/bootstrap.json.gz';OUT=ROOT/'data/research/transition-source-retention-schedulefirst-2019.json'
S=importlib.util.spec_from_file_location('sg',ROOT/'scripts'/'research-transition-shortgap-fidelity-2019.py')
sg=importlib.util.module_from_spec(S);S.loader.exec_module(sg);n=sg.nearest
TARGETS=list(sg.nearest.CHOSEN)
SCHED=re.compile(r'\b(?:PORTFOLIO|SCHEDULE) OF INVESTMENTS\b',re.I);COMMON=re.compile(r'\bCOMMON STOCKS?\b',re.I)

def first(filings):
 d={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in d:d[sid]=f
 return d
def base(s):
 x=n.norm(s);x=re.sub(r'\bCLASS\s+[A-Z0-9]+\b',' ',x);x=re.sub(r'\bSHARES?\b',' ',x);return ' '.join(x.split())
def parse_block(lines):
 rows=[];inside=False
 for raw in lines:
  line=n.clean(raw)
  if COMMON.search(line):inside=True;continue
  if inside and n.STOP_RE.search(line):inside=False;continue
  if not inside:continue
  cells=[n.clean(c) for c in re.split(r'\t+',raw) if n.clean(c) not in {'','$','—','-'}]
  nums=[(k,n.num(c)) for k,c in enumerate(cells) if n.NUM_RE.match(c)]
  if len(nums)>=2 and nums[0][0]>0:
   desc=' '.join(cells[:nums[0][0]]).strip()
   if desc and not desc.lower().startswith('total '):rows.append({'raw':desc,'base':base(desc)})
 return rows
def match(target,bases):
 t=base(target)
 if t in bases:return t,'exact'
 cand=[]
 for x in bases:
  short,long=(t,x) if len(t)<=len(x) else (x,t)
  if len(short)>=20 and long.startswith(short):cand.append(x)
 return (cand[0],'unique_prefix') if len(cand)==1 else (None,None)

def main():
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;fs=first(filings)
 names={sid:(fs[sid].get('seriesName') or fs[sid].get('fundName') or '') for sid in TARGETS if sid in fs}
 # All eight share the same fixed ETFMG N-CSR source.
 cik,acc,form,rd=sg.nearest.CHOSEN[TARGETS[0]];hit=n.locate_doc(n.docs(cik,acc,form),names[TARGETS[0]])
 if not hit:raise RuntimeError('ETFMG document not found')
 text=hit[3];lines=text.splitlines();markers=[]
 for i,x in enumerate(lines):
  if not SCHED.search(x):continue
  common=next((k for k in range(i,min(len(lines),i+21)) if COMMON.search(lines[k])),None)
  if common is None:continue
  # Assign real schedule to nearest preceding exact fixed registered series title.
  cand=[]
  for sid,name in names.items():
   hits=[p for p in range(max(0,i-260),i+1) if name.lower() in lines[p].lower()]
   if hits:cand.append((i-hits[-1],hits[-1],sid))
  if cand:
   dist,title,sid=sorted(cand)[0];markers.append({'line':i,'common':common,'seriesId':sid,'titleLine':title,'distance':dist})
 grouped={sid:[] for sid in names}
 for mi,m in enumerate(markers):
  end=markers[mi+1]['line'] if mi+1<len(markers) else min(len(lines),m['line']+1200)
  grouped[m['seriesId']].extend(parse_block(lines[m['line']:end]))
 rows=[]
 for sid,name in names.items():
  uniq={}
  for r in grouped[sid]:uniq.setdefault(r['base'],r)
  legacy=list(uniq.values());bases=list(uniq);ph=[h for h in fs[sid].get('holdings',[]) if h.get('issuerName')]
  matched=[];un=[]
  for h in ph:
   x,method=match(h['issuerName'],bases);rec={'nportIssuer':h['issuerName'],'symbol':h.get('symbol'),'legacyBase':x,'method':method}
   (matched if x else un).append(rec)
  r={'seriesId':sid,'seriesName':name,'days':(date.fromisoformat(fs[sid]['reportDate'])-date.fromisoformat(rd)).days,'assignedSchedulePages':sum(m['seriesId']==sid for m in markers),'legacyCommonStocks':len(legacy),'nportFilteredHoldings':len(ph),'nportRetained':len(matched),'nportRetentionRate':len(matched)/len(ph) if ph else None,'unmatchedNport':un}
  rows.append(r);print('RETENTION',json.dumps(r),flush=True)
 valid=[r for r in rows if r['legacyCommonStocks']>=10 and r['nportFilteredHoldings']]
 out={'purpose':'Schedule-first structural source-retention for all eight metadata-preregistered short-gap ETFMG series. A portfolio page is accepted only when a Schedule/Portfolio of Investments marker has COMMON STOCKS within the next 20 lines, then assigned to the nearest preceding exact registered series title. No overlap, ranks, or returns used for page selection.','acceptedSchedulePages':len(markers),'validSeries':len(valid),'medianRetention':statistics.median([r['nportRetentionRate'] for r in valid]) if valid else None,'minimumRetention':min([r['nportRetentionRate'] for r in valid]) if valid else None,'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
