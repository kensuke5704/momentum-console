#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-raw-header-country-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur);old=cur.old
NAME_PATTERNS=[re.compile(r'COMPANY\s+CONFORMED\s+NAME:\s*([^\n\r<]+)',re.I),re.compile(r'<CONFORMED-NAME>\s*([^\n\r<]+)',re.I)]
STATE_PATTERNS=[re.compile(r'STATE\s+OF\s+INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),re.compile(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})',re.I)]

def parts(archive_url):
 m=re.search(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/',archive_url,re.I)
 if not m:return None
 cik,ad=m.group(1),m.group(2);acc=f'{ad[:10]}-{ad[10:12]}-{ad[12:]}'
 return cik,ad,acc
def urls(archive_url):
 p=parts(archive_url)
 if not p:return []
 cik,ad,acc=p;base=f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/'
 return [base+acc+'.hdr.sgml',base+acc+'.txt',base+acc+'-index-headers.html']
def names(text):
 out=[]
 for pat in NAME_PATTERNS: out += [m.group(1).strip() for m in pat.finditer(text)]
 return list(dict.fromkeys(out))
def state(text):
 for pat in STATE_PATTERNS:
  m=pat.search(text)
  if m:return m.group(1).upper()
 return None

def main():
 d=json.loads(SRC.read_text());unknown=sorted([r for r in d['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:10]
 outrows=[]
 for row in unknown:
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
  target=old.normalize_name(row['issuer']);cm=cur.CM.get(row['ticker'].upper(),[]);exact=[x for x in cm if x.get('normalizedTitle')==target]
  if len(exact)==1:
   rec['seedCik']=exact[0]['cik']
   try:
    b=old.browse_cik(rec['seedCik'],row['asOfReportDate']);rec['archiveCount']=len(b.get('archiveUrls',[]));seen=set()
    for au in b.get('archiveUrls',[])[:12]:
     for u in urls(au):
      if u in seen:continue
      seen.add(u)
      try:
       text,tr=old.get(u,timeout=10);ns=names(text);st=state(text);ok=any(old.normalize_name(n)==target for n in ns)
       rec.setdefault('attempts',[]).append({'url':u,'transport':tr,'nameMatch':ok,'names':ns[:4],'stateCode':st,'length':len(text)})
       if ok and st:
        rec.update({'classification':'US' if st in old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_RAW_SEC_HEADER_NAME_VALIDATED','sourceUrl':u});break
      except Exception as e:rec.setdefault('attempts',[]).append({'url':u,'error':type(e).__name__})
     if rec['classification']!='UNKNOWN':break
     time.sleep(.03)
   except Exception as e:rec['browseError']=type(e).__name__
  outrows.append(rec);print('RAWHEADER',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','seedCik','archiveCount','classification','stateCode','resolutionSource']}),flush=True)
 resolved=[r for r in outrows if r['classification']!='UNKNOWN']
 out={'purpose':'Fast top-10 UNKNOWN country pilot testing raw historical SEC header resources (.hdr.sgml, complete submission .txt, then index-headers) after exact-name current ticker CIK seed. Classification requires historical company-name match and filing-time state.','sampleCount':len(outrows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r['aggregateWeight']) for r in resolved),'sampleWeight':sum(float(r['aggregateWeight']) for r in outrows),'results':outrows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
