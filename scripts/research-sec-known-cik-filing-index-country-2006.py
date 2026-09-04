#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
OUT=ROOT/'data/research/sec-known-cik-filing-index-country-2006.json'
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)
STATE_RE=re.compile(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I)
ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)

def idx_urls(doc):
 m=ARCH_RE.search(doc)
 if not m:return []
 cik,compact=m.group(1),m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}'
 base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index';return [base+'.htm',base+'.html']
def main():
 data=json.loads(COUNTRY.read_text());pit=json.loads(PIT.read_text());sf={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')}
 pop=[]
 for r in data['identityRows']:
  if r.get('classification')!='UNKNOWN':continue
  ciks=set(str(x).zfill(10) for x in (r.get('ciks') or []) if str(x).strip())
  if len(ciks)==1:pop.append((r,next(iter(ciks))))
 rows=[]
 for row,cik in pop:
  dates=sorted(sf[s] for s in (row.get('seriesIds') or []) if s in sf);cutoff=dates[0] if dates else row.get('asOfReportDate') or '2006-12-31'
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','seriesIds','asOfReportDate']};rec.update({'knownHistoricalCik':cik,'countryEvidenceCutoff':cutoff,'classification':'UNKNOWN'})
  params={'action':'getcompany','CIK':cik,'type':'10-K','dateb':cutoff.replace('-',''),'owner':'exclude','count':'10'}
  try:b=old.parse_browse(old.sec_url(params))
  except Exception:b={}
  for doc in b.get('archiveUrls',[])[:6]:
   found=False
   for iu in idx_urls(doc):
    try:text,tr=old.get(iu,timeout=12)
    except Exception:continue
    sm=STATE_RE.search(text)
    if not sm:continue
    code=sm.group(1).upper();rec.update({'classification':'US' if code in old.US_CODES else 'NON_US','stateCode':code,'indexUrl':iu,'transport':tr,'resolutionSource':'EXISTING_UNIQUE_HISTORICAL_CIK_10K_PIT_FILING_INDEX'});found=True;break
   if found:break
  rows.append(rec);print('KNOWN_CIK',json.dumps(rec),flush=True);time.sleep(.03)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Resolve only prior UNKNOWN identities that already had exactly one historical SEC CIK from the frozen PIT resolver. No current ticker metadata is used. Country evidence is historical 10-K filing-index State of Incorp. available no later than the earliest contributing legacy fund filingDate. No returns/ranks used.','candidateCount':len(rows),'candidateWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
