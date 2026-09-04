#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
OUT=ROOT/'data/research/sec-filing-date-country-fast-2006.json'
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
 sf={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')}
 unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:50]
 rows=[]
 for row in unknown:
  dates=sorted(sf[s] for s in (row.get('seriesIds') or []) if s in sf);cutoff=dates[0] if dates else row.get('asOfReportDate') or '2006-12-31'
  ticker=str(row.get('ticker') or '').upper();target=cur.old.normalize_name(row.get('issuer') or '')
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','seriesIds','asOfReportDate']};rec.update({'countryEvidenceCutoff':cutoff,'classification':'UNKNOWN'})
  exact=[x for x in cur.CM.get(ticker,[]) if x.get('normalizedTitle')==target]
  if len(exact)==1:
   seed=exact[0];params={'action':'getcompany','CIK':seed['cik'],'type':'10-K','dateb':cutoff.replace('-',''),'owner':'exclude','count':'10'}
   try:b=cur.old.parse_browse(cur.old.sec_url(params))
   except Exception:b={}
   for doc in b.get('archiveUrls',[])[:6]:
    done=False
    for iu in index_urls(doc):
     try:text,tr=cur.old.get(iu,timeout=12)
     except Exception:continue
     sm=STATE_RE.search(text)
     if not sm:continue
     code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'indexUrl':iu,'transport':tr,'resolutionSource':'EXACT_CURRENT_TICKER_CIK_10K_PIT_INDEX_BY_FUND_FILING_DATE'});done=True;break
    if done:break
  rows.append(rec);print('FAST',json.dumps(rec),flush=True);time.sleep(.03)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Fast equivalent of the preregistered filingDate PIT country route. Restricts SEC browse discovery to historical 10-K filings by the earliest public legacy fund filingDate, but keeps the same exact ticker+issuer CIK seed and historical filing-index State of Incorp. evidence requirements. No returns/ranks used.','sampleCount':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
