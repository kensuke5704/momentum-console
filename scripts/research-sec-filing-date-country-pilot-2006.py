#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
OUT=ROOT/'data/research/sec-filing-date-country-pilot-2006.json'
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
 data=json.loads(COUNTRY.read_text());pit=json.loads(PIT.read_text())
 series_filing={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')}
 unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:50]
 rows=[];cm=cur.CM
 for row in unknown:
  series=row.get('seriesIds') or []
  dates=sorted(series_filing[s] for s in series if s in series_filing)
  cutoff=dates[0] if dates else row.get('asOfReportDate') or '2006-12-31'
  ticker=str(row.get('ticker') or '').upper();issuer=row.get('issuer') or '';target=cur.old.normalize_name(issuer)
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','seriesIds','asOfReportDate']};rec['countryEvidenceCutoff']=cutoff;rec['classification']='UNKNOWN'
  exact=[x for x in cm.get(ticker,[]) if x.get('normalizedTitle')==target]
  if len(exact)==1:
   seed=exact[0]
   try:b=cur.old.browse_cik(seed['cik'],cutoff)
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
     code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'indexUrl':iu,'transport':tr,'resolutionSource':'CURRENT_TICKER_EXACT_NAME_CIK_THEN_PIT_FILING_INDEX_BY_FUND_FILING_DATE'})
     break
    if rec['classification']!='UNKNOWN':break
  rows.append(rec);print('PILOT',json.dumps(rec),flush=True);time.sleep(.05)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'UNKNOWN-only PIT country pilot using the earliest public legacy fund filingDate for each mapped identity as the external-evidence cutoff. This is the first date the N-Q holdings themselves are public, so issuer SEC metadata already public by that date is PIT-safe. Current ticker metadata only seeds a CIK on unique exact normalized ticker+issuer match; classification comes solely from historical filing-index State of Incorp. No returns/ranks used.','cutoffRule':'For each identity use the earliest filingDate among its contributing legacy ETF series; never use issuer evidence published after that fund filingDate.','sampleCount':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
