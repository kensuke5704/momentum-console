#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json';PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
SHARD=int(os.environ.get('SHARD_INDEX','0'));N=int(os.environ.get('SHARD_COUNT','12'));OUT=ROOT/f'data/research/sec-issuer-name-filing-date-country-shard-{SHARD}-2006.json'
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py');old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)
STATE_RE=re.compile(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I);ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)
def idx_urls(doc):
 m=ARCH_RE.search(doc)
 if not m:return []
 cik,compact=m.group(1),m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}';base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index';return [base+'.htm',base+'.html']
def issuer_search(query,cutoff):
 return old.parse_browse(old.sec_url({'action':'getcompany','company':query,'type':'10-K','dateb':cutoff.replace('-',''),'owner':'exclude','count':'10'}))
def cik_search(cik,cutoff):
 return old.parse_browse(old.sec_url({'action':'getcompany','CIK':cik,'type':'10-K','dateb':cutoff.replace('-',''),'owner':'exclude','count':'10'}))
def resolve(row,sf):
 dates=sorted(sf[s] for s in (row.get('seriesIds') or []) if s in sf);cutoff=dates[0] if dates else row.get('asOfReportDate') or '2006-12-31';target=old.normalize_name(row.get('issuer') or '')
 rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','occurrenceCount','seriesIds','asOfReportDate']};rec.update({'countryEvidenceCutoff':cutoff,'classification':'UNKNOWN'})
 direct={};candidates={}
 for q in old.issuer_query_variants(row.get('issuer') or ''):
  try:b=issuer_search(q,cutoff)
  except Exception:continue
  ciks=b.get('ciksFromArchive') or []
  if b.get('archiveUrls') and len(ciks)==1:direct[ciks[0]]=b
  for c in b.get('companyCandidates') or []:
   if c.get('normalizedName')==target:candidates[c['cik']]=c
  time.sleep(.02)
 cik=None;b=None;source=None
 if len(direct)==1:
  cik,b=next(iter(direct.items()));source='ISSUER_10K_DIRECT_SINGLE_CIK'
 elif len(candidates)==1:
  cik=next(iter(candidates));source='ISSUER_10K_EXACT_CANDIDATE_SINGLE_CIK'
  try:b=cik_search(cik,cutoff)
  except Exception:b=None
 if not cik or not b or not b.get('archiveUrls'):return rec
 for doc in b.get('archiveUrls',[])[:6]:
  for iu in idx_urls(doc):
   try:text,tr=old.get(iu,timeout=12)
   except Exception:continue
   sm=STATE_RE.search(text)
   if not sm:continue
   code=sm.group(1).upper();rec.update({'classification':'US' if code in old.US_CODES else 'NON_US','stateCode':code,'historicalCik':cik,'indexUrl':iu,'transport':tr,'resolutionSource':source+'_PIT_FILING_INDEX'});return rec
 return rec
def main():
 data=json.loads(COUNTRY.read_text());pit=json.loads(PIT.read_text());sf={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')};pop=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:(str(r.get('ticker') or ''),str(r.get('securityId') or ''),str(r.get('issuer') or '')));shard=[r for i,r in enumerate(pop) if i%N==SHARD]
 rows=[]
 for i,row in enumerate(shard,1):rec=resolve(row,sf);rows.append(rec);print(f'{i}/{len(shard)}',json.dumps(rec),flush=True)
 resolved=[r for r in rows if r['classification']!='UNKNOWN'];out={'purpose':'Full UNKNOWN-only historical issuer-name route using 10-K search by earliest contributing fund filingDate. Accept a CIK only from one direct historical result or one exact-normalized historical company candidate, then classify solely from historical filing-index State of Incorp. No current metadata, fuzzy matching, returns or ranks used.','shardIndex':SHARD,'shardCount':N,'populationUnknownCount':len(pop),'shardCountActual':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'rows':rows};OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
