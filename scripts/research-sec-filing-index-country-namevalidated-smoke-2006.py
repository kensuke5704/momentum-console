#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-filing-index-country-namevalidated-smoke-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
STATE_RE=re.compile(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I)
ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)
LEGAL={'CORP','CORPORATION','INC','INCORPORATED','CO','COMPANY','LTD','LIMITED','PLC'}

def index_urls(doc_url:str):
 m=ARCH_RE.search(doc_url)
 if not m:return []
 cik,compact=m.group(1),m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}'
 base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index'
 return [base+'.htm',base+'.html']
def key(s:str):
 n=cur.old.normalize_name(s)
 toks=[t for t in n.split() if t not in LEGAL]
 return ' '.join(toks)
def historical_name_match(text:str,issuer:str):
 # filing-index header appears before the documents table; only inspect the leading region
 hdr=text[:12000]
 hk=key(hdr);ik=key(issuer)
 return bool(ik and (ik in hk or hk.startswith(ik)))

def main():
 data=json.loads(SRC.read_text())
 unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:5]
 cm=cur.CM;rows=[]
 for row in unknown:
  ticker=str(row.get('ticker') or '').upper();issuer=row.get('issuer') or '';dateb=row.get('asOfReportDate') or '2006-12-31';target=cur.old.normalize_name(issuer)
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
  exact=[x for x in cm.get(ticker,[]) if x.get('normalizedTitle')==target]
  candidates=exact if len(exact)==1 else (cm.get(ticker,[]) if len(cm.get(ticker,[]))==1 else [])
  rec['seedMode']='EXACT_TICKER_ISSUER' if len(exact)==1 else ('UNIQUE_TICKER' if len(candidates)==1 else 'NONE')
  if len(candidates)==1:
   seed=candidates[0];rec['seedCik']=seed['cik'];rec['seedTitle']=seed.get('title')
   try:b=cur.old.browse_cik(seed['cik'],dateb)
   except Exception as e:b={'error':repr(e)}
   rec['archiveUrlCount']=len(b.get('archiveUrls',[]))
   seen=set()
   for doc in b.get('archiveUrls',[])[:8]:
    for iu in index_urls(doc):
     if iu in seen:continue
     seen.add(iu)
     try:text,tr=cur.old.get(iu,timeout=15)
     except Exception:continue
     if not historical_name_match(text,issuer):continue
     rec['historicalNameValidated']=True
     sm=STATE_RE.search(text)
     if not sm:continue
     code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'indexUrl':iu,'transport':tr,'resolutionSource':'CURRENT_TICKER_UNIQUE_OR_EXACT_CIK_THEN_PIT_INDEX_NAME_AND_STATE'})
     break
    if rec['classification']!='UNKNOWN':break
  rows.append(rec);print('SMOKE',json.dumps(rec),flush=True);time.sleep(.03)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Five-identity structural smoke test. Current ticker may seed a CIK only by exact ticker+issuer or a unique ticker. Classification requires historical filing-index issuer-name validation and historical State of Incorp.; current state is never used.','sampleCount':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
