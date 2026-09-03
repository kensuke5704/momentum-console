#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
old=cur.old
IDX=int(os.environ['SHARD_INDEX']); COUNT=int(os.environ.get('SHARD_COUNT','12'))
SRC=ROOT/f'data/research/sec-us-attribution-full-shard-{IDX:02d}-of-{COUNT:02d}-2006.json'
OUT=ROOT/f'data/research/sec-us-attribution-unknown-retry-{IDX:02d}-of-{COUNT:02d}-2006.json'
STATE_PATTERNS=[
 re.compile(r'State\s+of\s+Inc(?:orp(?:oration)?)?\.?\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I),
 re.compile(r'STATE-OF-INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),
 re.compile(r'State or other jurisdiction of incorporation[^A-Z0-9]{0,100}([A-Z]{2})\b',re.I),
 re.compile(r'STATE\s+OF\s+INCORPORATION[^A-Z0-9]{0,40}([A-Z0-9]{2,3})\b',re.I),
]

def find_state(text):
 for p in STATE_PATTERNS:
  m=p.search(text)
  if m:return m.group(1).upper(),p.pattern
 return None,None

def browse_10k_cik(cik,dateb):
 url='https://www.sec.gov/cgi-bin/browse-edgar?'+urllib.parse.urlencode({'action':'getcompany','CIK':cik,'type':'10-K','dateb':dateb.replace('-',''),'owner':'exclude','count':'40'})
 b=old.parse_browse(url);return b

def candidate_ciks(row):
 out=[]
 def add(x):
  if x:
   x=str(x).zfill(10)
   if x not in out:out.append(x)
 add(row.get('seedCik'))
 for x in row.get('ciks',[]) or []:add(x)
 add((row.get('candidate') or {}).get('cik'))
 ticker=str(row.get('ticker') or '').upper(); target=old.normalize_name(row.get('issuer') or '')
 exact=[x for x in cur.CM.get(ticker,[]) if x.get('normalizedTitle')==target]
 if len(exact)==1:add(exact[0].get('cik'))
 try:
  resolved,audits=old.resolve_issuer_variants(row.get('issuer') or '',row.get('asOfReportDate'))
  if resolved:add(resolved.get('cik'))
 except Exception:pass
 return out

def retry(row):
 if row.get('classification')!='UNKNOWN':return row
 ciks=candidate_ciks(row); attempts=[]
 for cik in ciks[:8]:
  try:
   b=browse_10k_cik(cik,row['asOfReportDate']); a={'cik':cik,'archiveCount':len(b.get('archiveUrls',[])),'transport':b.get('transport')}
   for url in (b.get('archiveUrls') or [])[:20]:
    try:
     text,tr=old.get(url,timeout=12); state,pattern=find_state(text)
     if state:
      a.update({'stateCode':state,'filingUrl':url,'filingTransport':tr,'pattern':pattern})
      attempts.append(a)
      return {**row,'classification':'US' if state in old.US_CODES else 'NON_US','resolutionSource':'TEN_K_SCOPED_HISTORICAL_HEADER_RETRY','stateCode':state,'retryCik':cik,'retryAttempts':attempts}
    except Exception as e:a.setdefault('errors',[]).append(type(e).__name__)
   attempts.append(a)
  except Exception as e:attempts.append({'cik':cik,'error':type(e).__name__})
  time.sleep(.05)
 return {**row,'retryCikCandidates':ciks,'retryAttempts':attempts}

def main():
 src=json.loads(SRC.read_text()); results=[]
 for i,row in enumerate(src.get('results',[]),1):
  r=retry(row);results.append(r)
  if row.get('classification')=='UNKNOWN':print('RETRY',json.dumps({k:r.get(k) for k in ['ticker','issuer','aggregateWeight','classification','resolutionSource','stateCode','retryCik']}),flush=True)
 counts={k:sum(r.get('classification')==k for r in results) for k in ['US','NON_US','UNKNOWN']}
 weights={k:sum(float(r.get('aggregateWeight') or 0) for r in results if r.get('classification')==k) for k in ['US','NON_US','UNKNOWN']}
 changed=sum(1 for before,after in zip(src.get('results',[]),results) if before.get('classification')=='UNKNOWN' and after.get('classification')!='UNKNOWN')
 out={'year':2006,'purpose':'Retry only prior UNKNOWN mapped identities using 10-K-scoped historical SEC filing searches and broader filing-time incorporation header patterns. Existing resolved classifications are frozen. No returns/ranks used.','shardIndex':IDX,'shardCount':COUNT,'changedUnknownToResolved':changed,'classificationCounts':counts,'classificationWeights':weights,'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
