#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/legacy-q1-index-discovery-sample-2006.json'
SPEC=importlib.util.spec_from_file_location('master',ROOT/'scripts'/'research-sec-legacy-series-header-pilot-2006.py')
master=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(master)
UA=master.UA
SL=re.compile(r'^Series\s+\[(S\d{9})\]\([^\)]*\)(.+?)\s*$',re.I)
CL=re.compile(r'^Class/Contract\s+\[(C\d{9})\]\([^\)]*\)(.+?)\s+([A-Z][A-Z0-9.\-]{0,9})\s*$',re.I)
def get(url):
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=20).read().decode('utf-8','replace'),u
  except Exception:pass
 raise RuntimeError('fetch failed')
def parse(text):
 lines=[x.strip() for x in text.splitlines() if x.strip()];out=[]
 for i,line in enumerate(lines):
  sm=SL.match(line)
  if not sm:continue
  for nxt in lines[i+1:i+4]:
   cm=CL.match(nxt)
   if cm:
    out.append({'seriesId':sm.group(1).upper(),'seriesName':' '.join(sm.group(2).split()),'classId':cm.group(1).upper(),'ticker':cm.group(3).upper()});break
 return out
def main():
 text,tr=master.get_index(1);rows=[]
 for line in text.splitlines():
  p=line.split('|')
  if len(p)>=5 and p[2].strip().upper()=='N-Q': rows.append({'cik':p[0].strip(),'company':p[1].strip(),'dateFiled':p[3].strip(),'filename':p[4].strip()})
 rows=sorted(rows,key=lambda x:(x['dateFiled'],x['cik'],x['filename']));n=len(rows);N=min(64,n);pos=sorted(set(min(n-1,(i*n)//N) for i in range(N)));sample=[rows[i] for i in pos];results=[]
 for j,r in enumerate(sample,1):
  path=r['filename'];base=path.rsplit('/',1)[0];acc=path.rsplit('/',1)[1].replace('.txt','');url='https://www.sec.gov/Archives/'+base+'/'+acc+'-index.html'
  try:
   t,transport=get(url);pairs=parse(t);res={**r,'indexUrl':url,'transport':transport,'pairCount':len(pairs),'pairs':pairs}
  except Exception as e:res={**r,'indexUrl':url,'pairCount':0,'pairs':[],'error':type(e).__name__}
  results.append(res);print('SAMPLE',json.dumps({'i':j,'company':r['company'],'date':r['dateFiled'],'pairCount':res['pairCount'],'error':res.get('error')}),flush=True);time.sleep(.06)
 tickered=[r for r in results if r['pairCount']>0];pairs=[p for r in tickered for p in r['pairs']]
 out={'purpose':'Production-independent feasibility sample for scalable 2006 source discovery: 64 deterministic equal-quantile Q1 N-Q filings from official SEC master index, then Series/Class/Ticker extraction from filing index pages. No holdings, ranks, or returns used.','q1NqFilingCount':n,'sampleCount':len(sample),'fetchSuccess':sum('error' not in r for r in results),'sampleWithTickeredSeries':len(tickered),'tickeredFilingRate':len(tickered)/len(sample) if sample else 0,'seriesClassPairsFound':len(pairs),'uniqueSeriesFound':len({p['seriesId'] for p in pairs}),'results':results,'masterTransport':tr}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
