#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-index-headers-country-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
old=cur.old
NAME_RE=re.compile(r'COMPANY\s+CONFORMED\s+NAME:\s*([^\n\r<]+)',re.I)
STATE_RES=[
 re.compile(r'STATE\s+OF\s+INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),
 re.compile(r'State\s+of\s+Incorp\.?:\s*([A-Z0-9]{2,3})',re.I),
]

def acc_from_dir(d):
 d=''.join(ch for ch in d if ch.isdigit())
 if len(d)!=18:return None
 return f'{d[:10]}-{d[10:12]}-{d[12:]}'
def header_url(archive_url):
 m=re.search(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/',archive_url,re.I)
 if not m:return None
 cik,ad=m.group(1),m.group(2);acc=acc_from_dir(ad)
 if not acc:return None
 return f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index-headers.html'
def hist_name_ok(target,text):
 names=[m.group(1).strip() for m in NAME_RE.finditer(text)]
 nt=old.normalize_name(target)
 return any(old.normalize_name(n)==nt for n in names),names[:5]
def state_of(text):
 for pat in STATE_RES:
  m=pat.search(text)
  if m:return m.group(1).upper()
 return None

def main():
 data=json.loads(SRC.read_text())
 unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:50]
 results=[]
 for row in unknown:
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
  cm=cur.CM.get((row.get('ticker') or '').upper(),[])
  target=old.normalize_name(row.get('issuer') or '')
  exact=[x for x in cm if x.get('normalizedTitle')==target]
  if len(exact)==1:
   cik=exact[0]['cik'];rec['seedCik']=cik
   try:
    b=old.browse_cik(cik,row['asOfReportDate']);rec['archiveCount']=len(b.get('archiveUrls',[]))
    seen=[]
    for au in b.get('archiveUrls',[])[:16]:
     hu=header_url(au)
     if not hu or hu in seen:continue
     seen.append(hu)
     try:
      text,tr=old.get(hu,timeout=12);ok,names=hist_name_ok(row['issuer'],text);st=state_of(text)
      rec.setdefault('attempts',[]).append({'headerUrl':hu,'transport':tr,'nameMatch':ok,'names':names,'stateCode':st})
      if ok and st:
       rec.update({'classification':'US' if st in old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_INDEX_HEADERS_NAME_VALIDATED','headerUrl':hu});break
     except Exception as e:rec.setdefault('attempts',[]).append({'headerUrl':hu,'error':type(e).__name__})
     time.sleep(.05)
  results.append(rec);print('HEADER',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','seedCik','archiveCount','classification','stateCode','resolutionSource']}),flush=True)
 resolved=[r for r in results if r['classification']!='UNKNOWN']
 out={'purpose':'UNKNOWN-only PIT country pilot using current ticker only as an exact-name CIK seed; actual classification requires a historical SEC filing index-headers page by the legacy report date, historical COMPANY CONFORMED NAME matching the legacy issuer, and filing-time STATE OF INCORPORATION. No current state, returns, or ranks used.','sampleCount':len(results),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in results),'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
