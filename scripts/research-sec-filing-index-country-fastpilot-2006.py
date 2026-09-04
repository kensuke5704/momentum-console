#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-filing-index-country-fastpilot-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
STATE_RE=re.compile(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)\s*:?\s*([A-Z0-9]{2,3})',re.I)
ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)
def index_url(doc):
 m=ARCH_RE.search(doc)
 if not m:return None
 cik,compact=m.group(1),m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}'
 return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index.html'
def main():
 data=json.loads(SRC.read_text());unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:10]
 rows=[]
 for row in unknown:
  ticker=str(row.get('ticker') or '').upper();issuer=row.get('issuer') or '';dateb=row.get('asOfReportDate') or '2006-12-31';target=cur.old.normalize_name(issuer)
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
  exact=[x for x in cur.CM.get(ticker,[]) if x.get('normalizedTitle')==target]
  if len(exact)==1:
   seed=exact[0]
   try:b=cur.old.browse_cik(seed['cik'],dateb)
   except Exception:b={}
   urls=[]
   for doc in b.get('archiveUrls',[]):
    iu=index_url(doc)
    if iu and iu not in urls:urls.append(iu)
   for iu in urls[:4]:
    try:text,tr=cur.old.get(iu,timeout=10)
    except Exception:continue
    sm=STATE_RE.search(text)
    if sm:
     code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'indexUrl':iu,'transport':tr,'resolutionSource':'CURRENT_TICKER_EXACT_NAME_CIK_THEN_PIT_FILING_INDEX'});break
  rows.append(rec);print('FAST',json.dumps(rec),flush=True);time.sleep(.03)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Fast structural check of historical SEC filing-index State of Incorp country resolver on top-10 remaining UNKNOWN by weight; same rules as full pilot, limited to first four unique historical accessions.','sampleCount':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
