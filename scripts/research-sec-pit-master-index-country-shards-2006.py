#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time,urllib.request
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
IDX=int(os.environ['SHARD_INDEX']);COUNT=int(os.environ['SHARD_COUNT'])
OUT=ROOT/f'data/research/sec-pit-master-index-country-{IDX:02d}-of-{COUNT:02d}-2006.json'
SPEC=importlib.util.spec_from_file_location('legacy',ROOT/'scripts'/'research-sec-legacy-series-header-pilot-2006.py')
legacy=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(legacy)
STATE=[re.compile(r'STATE-OF-INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),re.compile(r'State\s+of\s+Inc(?:orp(?:oration)?)?\.?\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I),re.compile(r'State or other jurisdiction of incorporation[^A-Z0-9]{0,80}([A-Z]{2})\b',re.I)]
US={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
UA=legacy.UA

def norm(s):
 s=(s or '').upper().replace('&',' AND ')
 s=re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$','',s,flags=re.I)
 s=re.sub(r'\bTHE\b',' ',s);s=re.sub(r'\b(INCORPORATED|INCORPORATION)\b',' INC ',s);s=re.sub(r'\bCORPORATION\b',' CORP ',s);s=re.sub(r'\bCOMPANY\b',' CO ',s);s=re.sub(r'\bLIMITED\b',' LTD ',s);s=re.sub(r'\bHLDGS\b',' HOLDINGS ',s)
 return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def get_index(year,q):
 # Same proven SEC zip -> master.idx fallback pattern as the successful 2006 legacy discovery pilot.
 base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
 import io,zipfile
 last=None
 for attempt in range(4):
  try:
   req=urllib.request.Request(base+'/master.zip',headers=UA)
   with urllib.request.urlopen(req,timeout=75) as r:data=r.read(15_000_000)
   with zipfile.ZipFile(io.BytesIO(data)) as z:
    n=next(x for x in z.namelist() if x.lower().endswith('master.idx'));return z.read(n).decode('latin1','replace'),base+'/master.zip'
  except Exception as e:last=e;time.sleep(.4*(attempt+1))
 for attempt in range(4):
  for u in (base+'/master.idx','https://r.jina.ai/'+base+'/master.idx'):
   try:
    req=urllib.request.Request(u,headers=UA)
    with urllib.request.urlopen(req,timeout=75) as r:return r.read(45_000_000).decode('latin1','replace'),u
   except Exception as e:last=e
  time.sleep(.4*(attempt+1))
 raise RuntimeError(repr(last))
def get_filing(path):
 url='https://www.sec.gov/Archives/'+path.lstrip('/')
 last=None
 for attempt in range(3):
  for u in ('https://r.jina.ai/'+url,url):
   try:
    req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=25).read(4_000_000).decode('utf-8','replace'),u
   except Exception as e:last=e
  time.sleep(.2*(attempt+1))
 raise RuntimeError(repr(last))
def main():
 data=json.loads(SRC.read_text());unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or ''))
 # Build PIT 10-K index from 2005 + 2006. Each identity later filters date <= its own asOfReportDate.
 idx=[];transports={}
 for y in (2005,2006):
  for q in (1,2,3,4):
   try:
    text,tr=get_index(y,q);transports[f'{y}Q{q}']=tr
    for line in text.splitlines():
     p=line.split('|')
     if len(p)>=5 and p[2].strip().upper() in {'10-K','10-K/A','10-K405'}:idx.append({'cik':p[0].strip(),'company':p[1].strip(),'form':p[2].strip().upper(),'date':p[3].strip(),'path':p[4].strip()})
   except Exception as e:transports[f'{y}Q{q}']='ERROR:'+type(e).__name__
 by=defaultdict(list)
 for r in idx:by[norm(r['company'])].append(r)
 shard=[r for i,r in enumerate(unknown) if i%COUNT==IDX];rows=[]
 for i,row in enumerate(shard,1):
  target=norm(row.get('issuer'));asof=row.get('asOfReportDate') or '2006-12-31';cands=[x for x in by.get(target,[]) if x['date']<=asof];ciks=sorted({x['cik'] for x in cands});rec={k:row.get(k) for k in ['ticker','securityId','issuer','asOfReportDate','aggregateWeight']};rec.update({'normalizedIssuer':target,'candidateCiks':ciks,'candidateFilings':len(cands),'classification':'UNKNOWN'})
  if len(ciks)==1:
   # Prefer latest filing available by as-of.
   for cand in sorted(cands,key=lambda x:x['date'],reverse=True):
    try:
     text,tr=get_filing(cand['path']);code=None
     for pat in STATE:
      m=pat.search(text)
      if m:code=m.group(1).upper();break
     if code:
      rec.update({'classification':'US' if code in US else 'NON_US','stateCode':code,'resolvedCik':ciks[0],'filingDate':cand['date'],'filingPath':cand['path'],'transport':tr,'resolutionSource':'PIT_MASTER_EXACT_ISSUER_TO_10K'});break
    except Exception:pass
  rows.append(rec);print(f'{i}/{len(shard)}',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','classification','stateCode','candidateCiks','candidateFilings']}),flush=True)
 out={'purpose':'Residual UNKNOWN country attribution using only official 2005-2006 SEC master indexes. Exact normalized legacy issuer company-name -> unique historical CIK; classification only from a 10-K filed on/before each legacy report date. No current metadata, ranks, or returns used.','shardIndex':IDX,'shardCount':COUNT,'populationCount':len(unknown),'masterTransports':transports,'master10kRows':len(idx),'rowCount':len(rows),'resolvedCount':sum(r['classification']!='UNKNOWN' for r in rows),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows if r['classification']!='UNKNOWN'),'rows':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'rows','masterTransports'}}),flush=True);print('TRANSPORTS',json.dumps(transports),flush=True)
if __name__=='__main__':main()
