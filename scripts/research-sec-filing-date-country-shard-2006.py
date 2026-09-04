#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
SHARD=int(os.environ.get('SHARD_INDEX','0'));N=int(os.environ.get('SHARD_COUNT','12'))
OUT=ROOT/f'data/research/sec-filing-date-country-shard-{SHARD}-2006.json'
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

def resolve(row,sf):
 dates=sorted(sf[s] for s in (row.get('seriesIds') or []) if s in sf);cutoff=dates[0] if dates else row.get('asOfReportDate') or '2006-12-31'
 ticker=str(row.get('ticker') or '').upper();target=cur.old.normalize_name(row.get('issuer') or '')
 rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','occurrenceCount','seriesIds','asOfReportDate']};rec.update({'countryEvidenceCutoff':cutoff,'classification':'UNKNOWN'})
 exact=[x for x in cur.CM.get(ticker,[]) if x.get('normalizedTitle')==target]
 if len(exact)!=1:return rec
 seed=exact[0];params={'action':'getcompany','CIK':seed['cik'],'type':'10-K','dateb':cutoff.replace('-',''),'owner':'exclude','count':'10'}
 try:b=cur.old.parse_browse(cur.old.sec_url(params))
 except Exception:return rec
 for doc in b.get('archiveUrls',[])[:6]:
  for iu in index_urls(doc):
   try:text,tr=cur.old.get(iu,timeout=12)
   except Exception:continue
   sm=STATE_RE.search(text)
   if not sm:continue
   code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'indexUrl':iu,'transport':tr,'resolutionSource':'EXACT_CURRENT_TICKER_CIK_10K_PIT_INDEX_BY_FUND_FILING_DATE'});return rec
 return rec

def main():
 data=json.loads(COUNTRY.read_text());pit=json.loads(PIT.read_text());sf={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')}
 pop=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:(str(r.get('ticker') or ''),str(r.get('securityId') or ''),str(r.get('issuer') or '')))
 shard=[r for i,r in enumerate(pop) if i%N==SHARD]
 rows=[]
 for i,row in enumerate(shard,1):
  rec=resolve(row,sf);rows.append(rec);print(f'{i}/{len(shard)}',json.dumps(rec),flush=True);time.sleep(.03)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Full UNKNOWN-only PIT country shard using exact current ticker+issuer CIK seed, historical 10-K filing index State of Incorp., and earliest contributing legacy fund filingDate cutoff. Existing US/NON_US classifications remain frozen outside this shard. No returns/ranks used.','shardIndex':SHARD,'shardCount':N,'populationUnknownCount':len(pop),'shardCountActual':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
