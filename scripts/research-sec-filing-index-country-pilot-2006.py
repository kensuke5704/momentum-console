#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-filing-index-country-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
STATE_RE=re.compile(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I)
ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)

def index_urls(doc_url:str):
 m=ARCH_RE.search(doc_url)
 if not m:return []
 cik,compact=m.group(1),m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}'
 base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index'
 return [base+'.htm',base+'.html']

def main():
 data=json.loads(SRC.read_text());unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:50]
 cm=cur.CM;rows=[]
 for row in unknown:
  ticker=str(row.get('ticker') or '').upper();issuer=row.get('issuer') or '';dateb=row.get('asOfReportDate') or '2006-12-31';target=cur.old.normalize_name(issuer)
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
  exact=[x for x in cm.get(ticker,[]) if x.get('normalizedTitle')==target]
  if len(exact)==1:
   seed=exact[0]
   try:b=cur.old.browse_cik(seed['cik'],dateb)
   except Exception:b={}
   seen=set()
   for doc in b.get('archiveUrls',[])[:16]:
    for iu in index_urls(doc):
     if iu in seen:continue
     seen.add(iu)
     try:text,tr=cur.old.get(iu,timeout=18)
     except Exception:continue
     sm=STATE_RE.search(text)
     if not sm:continue
     code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'indexUrl':iu,'transport':tr,'resolutionSource':'CURRENT_TICKER_EXACT_NAME_CIK_THEN_PIT_FILING_INDEX'})
     break
    if rec['classification']!='UNKNOWN':break
  rows.append(rec);print('PILOT',json.dumps(rec),flush=True);time.sleep(.06)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'UNKNOWN-only PIT country pilot. Current ticker metadata may seed a CIK only on unique exact normalized ticker+issuer-name match. Country classification is taken only from historical SEC filing index State of Incorp. metadata available by the legacy report date. Markdown emphasis around SEC state codes is presentation-only and ignored. No current state, returns, or ranks used.','sampleCount':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
