#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
SHARD_INDEX=int(os.environ['SHARD_INDEX']);SHARD_COUNT=int(os.environ['SHARD_COUNT'])
OUT=ROOT/f'data/research/sec-raw-header-country-shard-{SHARD_INDEX:02d}-of-{SHARD_COUNT:02d}-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur);old=cur.old
NAME_PATTERNS=[re.compile(r'COMPANY\s+CONFORMED\s+NAME:\s*([^\n\r<]+)',re.I),re.compile(r'<CONFORMED-NAME>\s*([^\n\r<]+)',re.I)]
STATE_PATTERNS=[re.compile(r'STATE\s+OF\s+INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),re.compile(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})',re.I)]

def archive_parts(archive_url):
 m=re.search(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/',archive_url,re.I)
 if not m:return None
 cik,ad=m.group(1),m.group(2);acc=f'{ad[:10]}-{ad[10:12]}-{ad[12:]}'
 return cik,ad,acc
def candidate_urls(archive_url):
 p=archive_parts(archive_url)
 if not p:return []
 cik,ad,acc=p;base=f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/'
 return [base+acc+'.hdr.sgml',base+acc+'.txt',base+acc+'-index-headers.html']
def extract_names(text):
 out=[]
 for pat in NAME_PATTERNS:out += [m.group(1).strip() for m in pat.finditer(text)]
 return list(dict.fromkeys(out))
def extract_state(text):
 for pat in STATE_PATTERNS:
  m=pat.search(text)
  if m:return m.group(1).upper()
 return None
def resolve(row):
 rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
 target=old.normalize_name(row.get('issuer') or '');cm=cur.CM.get((row.get('ticker') or '').upper(),[]);exact=[x for x in cm if x.get('normalizedTitle')==target]
 if len(exact)!=1:return rec
 rec['seedCik']=exact[0]['cik']
 try:
  b=old.browse_cik(rec['seedCik'],row['asOfReportDate']);rec['archiveCount']=len(b.get('archiveUrls',[]));seen=set()
  for au in b.get('archiveUrls',[])[:12]:
   for u in candidate_urls(au):
    if u in seen:continue
    seen.add(u)
    try:
     text,tr=old.get(u,timeout=10);ns=extract_names(text);st=extract_state(text);ok=any(old.normalize_name(n)==target for n in ns)
     if ok and st:
      rec.update({'classification':'US' if st in old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_RAW_SEC_HEADER_NAME_VALIDATED','sourceUrl':u,'transport':tr});return rec
    except Exception:pass
   time.sleep(.03)
 except Exception as e:rec['browseError']=type(e).__name__
 return rec

def main():
 d=json.loads(SRC.read_text());unknown=sorted([r for r in d['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or '',r.get('issuer') or ''))
 shard=[r for i,r in enumerate(unknown) if i%SHARD_COUNT==SHARD_INDEX];results=[]
 for i,row in enumerate(shard,1):
  rec=resolve(row);results.append(rec);print(f'{i}/{len(shard)}',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','seedCik','archiveCount','classification','stateCode','resolutionSource']}),flush=True)
 counts={k:sum(1 for r in results if r['classification']==k) for k in ['US','NON_US','UNKNOWN']};weights={k:sum(float(r.get('aggregateWeight') or 0) for r in results if r['classification']==k) for k in counts}
 out={'year':2006,'purpose':'UNKNOWN-only shard using exact-name current ticker only as CIK seed; classification requires historical SEC raw header/complete-submission/index-header company-name match and filing-time state. Existing resolved classifications are frozen.','shardIndex':SHARD_INDEX,'shardCount':SHARD_COUNT,'unknownPopulationCount':len(unknown),'shardCountActual':len(shard),'classificationCounts':counts,'classificationWeights':weights,'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
