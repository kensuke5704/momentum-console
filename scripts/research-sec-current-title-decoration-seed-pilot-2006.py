#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-current-title-decoration-seed-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur);old=cur.old
NAME_PATTERNS=[re.compile(r'COMPANY\s+CONFORMED\s+NAME:\s*([^\n\r<]+)',re.I),re.compile(r'<CONFORMED-NAME>\s*([^\n\r<]+)',re.I)]
STATE_PATTERNS=[re.compile(r'STATE\s+OF\s+INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),re.compile(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})',re.I)]
JURIS_RE=re.compile(r'\s*/[A-Z0-9]{2,3}/?\s*$',re.I)

def structural_current_norm(title):return old.normalize_name(JURIS_RE.sub('',title or ''))
def parts(u):
 m=re.search(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/',u,re.I)
 if not m:return None
 cik,ad=m.group(1),m.group(2);acc=f'{ad[:10]}-{ad[10:12]}-{ad[12:]}'
 return cik,ad,acc
def header_urls(u):
 p=parts(u)
 if not p:return []
 cik,ad,acc=p;base=f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/'
 return [base+acc+'.hdr.sgml',base+acc+'.txt']
def names(text):
 a=[]
 for pat in NAME_PATTERNS:a += [m.group(1).strip() for m in pat.finditer(text)]
 return list(dict.fromkeys(a))
def state(text):
 for pat in STATE_PATTERNS:
  m=pat.search(text)
  if m:return m.group(1).upper()
 return None
def resolve(row):
 rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN';target=old.normalize_name(row['issuer']);cm=cur.CM.get(row['ticker'].upper(),[])
 baseline=[x for x in cm if x.get('normalizedTitle')==target]
 if baseline:return rec
 structural=[x for x in cm if structural_current_norm(x.get('title'))==target]
 if len(structural)!=1:return rec
 x=structural[0];rec.update({'seedCik':x['cik'],'seedCurrentTitle':x['title'],'seedSource':'CURRENT_TICKER_JURISDICTION_DECORATION_EXACT'})
 try:
  b=old.browse_cik(x['cik'],row['asOfReportDate']);rec['archiveCount']=len(b.get('archiveUrls',[]));seen=set()
  for au in b.get('archiveUrls',[])[:12]:
   for u in header_urls(au):
    if u in seen:continue
    seen.add(u)
    try:
     text,tr=old.get(u,timeout=8);ns=names(text);st=state(text);ok=any(old.normalize_name(n)==target for n in ns)
     if ok and st:
      rec.update({'classification':'US' if st in old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'DECORATION_SEED_THEN_PIT_RAW_HEADER','sourceUrl':u,'transport':tr});return rec
    except Exception:pass
   time.sleep(.02)
 except Exception as e:rec['browseError']=type(e).__name__
 return rec

def main():
 d=json.loads(SRC.read_text());unknown=sorted([r for r in d['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:50]
 rows=[]
 for r in unknown:
  q=resolve(r);rows.append(q);print('DECOR',json.dumps({k:q.get(k) for k in ['ticker','issuer','aggregateWeight','seedCik','seedCurrentTitle','classification','stateCode']}),flush=True)
 res=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Structural seed pilot for prior UNKNOWNs: remove only trailing SEC /XX/ jurisdiction decoration from current ticker title, require unique exact normalized issuer match, then classify only from historical raw SEC header with historical company-name match and filing-time state.','sampleCount':len(rows),'seededCount':sum(bool(r.get('seedCik')) for r in rows),'resolvedCount':len(res),'resolvedWeight':sum(float(r['aggregateWeight']) for r in res),'sampleWeight':sum(float(r['aggregateWeight']) for r in rows),'results':rows}
 OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
