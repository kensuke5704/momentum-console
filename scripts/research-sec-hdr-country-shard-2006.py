#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRY=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
SHARD=int(os.environ.get('SHARD_INDEX','0'));N=int(os.environ.get('SHARD_COUNT','12'))
OUT=ROOT/f'data/research/sec-hdr-country-shard-{SHARD}-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
old=cur.old
STATE_RE=re.compile(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})',re.I)
NAME_RE=re.compile(r'<CONFORMED-NAME>\s*([^\r\n<]+)',re.I)
INDEX_RE=re.compile(r'^(https?://[^\s]+/)(\d{10}-\d{2}-\d{6})-index\.html?$',re.I)

def hdr_url(index_url:str)->str|None:
 m=INDEX_RE.match(index_url)
 return m.group(1)+m.group(2)+'.hdr.sgml' if m else None

def cutoff_for(row,sf):
 dates=sorted(sf[s] for s in (row.get('seriesIds') or []) if s in sf)
 return dates[0] if dates else row.get('asOfReportDate') or '2006-12-31'

def browse_10k_cik(cik,cutoff):
 return old.parse_browse(old.sec_url({'action':'getcompany','CIK':cik,'type':'10-K','dateb':cutoff.replace('-',''),'owner':'exclude','count':'10'}))

def candidate_ciks(row,cutoff):
 # Priority is evidence quality only, never desired country/result.
 known=sorted(set(str(x).zfill(10) for x in (row.get('ciks') or []) if str(x).strip()))
 if len(known)==1:return [(known[0],'EXISTING_UNIQUE_HISTORICAL_CIK')]
 ticker=str(row.get('ticker') or '').upper();target=old.normalize_name(row.get('issuer') or '')
 exact=[x for x in cur.CM.get(ticker,[]) if x.get('normalizedTitle')==target]
 if len(exact)==1:return [(exact[0]['cik'],'CURRENT_TICKER_EXACT_NAME_CIK_SEED')]
 # Last route: historical issuer-name search, deterministic exact/single only.
 direct={};named={}
 for q in old.issuer_query_variants(row.get('issuer') or ''):
  try:b=old.parse_browse(old.sec_url({'action':'getcompany','company':q,'type':'10-K','dateb':cutoff.replace('-',''),'owner':'exclude','count':'10'}))
  except Exception:continue
  ciks=b.get('ciksFromArchive') or []
  if b.get('archiveUrls') and len(ciks)==1:direct[ciks[0]]=1
  for c in b.get('companyCandidates') or []:
   if c.get('normalizedName')==target:named[c['cik']]=1
  time.sleep(.01)
 pool=sorted(set(direct)|set(named))
 return [(pool[0],'HISTORICAL_ISSUER_NAME_SINGLE_CIK')] if len(pool)==1 else []

def resolve(row,sf):
 cutoff=cutoff_for(row,sf);target=old.normalize_name(row.get('issuer') or '')
 rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','occurrenceCount','seriesIds','asOfReportDate']};rec.update({'countryEvidenceCutoff':cutoff,'classification':'UNKNOWN'})
 cands=candidate_ciks(row,cutoff);rec['candidateCiks']=[c[0] for c in cands]
 if len(cands)!=1:return rec
 cik,seed_source=cands[0]
 try:b=browse_10k_cik(cik,cutoff)
 except Exception:return rec
 for idx in b.get('archiveUrls',[])[:10]:
  hu=hdr_url(idx)
  if not hu:continue
  try:text,tr=old.get(hu,timeout=12)
  except Exception:continue
  names=[x.strip() for x in NAME_RE.findall(text)]
  # Historical issuer identity must match. Current ticker name never supplies country evidence.
  if not names or not any(old.normalize_name(x)==target for x in names):continue
  sm=STATE_RE.search(text)
  if not sm:continue
  code=sm.group(1).upper();rec.update({'classification':'US' if code in old.US_CODES else 'NON_US','stateCode':code,'historicalCik':cik,'historicalNames':names[:3],'hdrUrl':hu,'transport':tr,'resolutionSource':seed_source+'_THEN_PIT_HDR_SGML'});return rec
 return rec

def main():
 data=json.loads(COUNTRY.read_text());pit=json.loads(PIT.read_text());sf={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')}
 pop=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:(str(r.get('ticker') or ''),str(r.get('securityId') or ''),str(r.get('issuer') or '')))
 shard=[r for i,r in enumerate(pop) if i%N==SHARD];rows=[]
 for i,row in enumerate(shard,1):
  rec=resolve(row,sf);rows.append(rec);print(f'{i}/{len(shard)}',json.dumps(rec),flush=True);time.sleep(.02)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Full UNKNOWN-only PIT country attribution using SEC accession .hdr.sgml. CIK may come from one already-known historical CIK, one exact current ticker+issuer seed, or one deterministic historical issuer-name result. Classification requires historical <CONFORMED-NAME> match and <STATE-OF-INCORPORATION> in an issuer 10-K header published no later than the earliest contributing legacy fund filingDate. No current state, fuzzy matching, returns or ranks used.','shardIndex':SHARD,'shardCount':N,'populationUnknownCount':len(pop),'shardCountActual':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
