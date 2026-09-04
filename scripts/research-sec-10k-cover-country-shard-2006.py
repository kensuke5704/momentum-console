#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
FINAL=ROOT/'data/research/country-final-structural-merge-2006.json'
PIT=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
SHARD=int(os.environ.get('SHARD_INDEX','0'));N=int(os.environ.get('SHARD_COUNT','12'))
OUT=ROOT/f'data/research/sec-10k-cover-country-shard-{SHARD}-2006.json'
SPEC=importlib.util.spec_from_file_location('hdr',ROOT/'scripts'/'research-sec-hdr-country-shard-2006.py')
hdr=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(hdr)
old=hdr.old
US_STATES={'ALABAMA':'AL','ALASKA':'AK','ARIZONA':'AZ','ARKANSAS':'AR','CALIFORNIA':'CA','COLORADO':'CO','CONNECTICUT':'CT','DELAWARE':'DE','FLORIDA':'FL','GEORGIA':'GA','HAWAII':'HI','IDAHO':'ID','ILLINOIS':'IL','INDIANA':'IN','IOWA':'IA','KANSAS':'KS','KENTUCKY':'KY','LOUISIANA':'LA','MAINE':'ME','MARYLAND':'MD','MASSACHUSETTS':'MA','MICHIGAN':'MI','MINNESOTA':'MN','MISSISSIPPI':'MS','MISSOURI':'MO','MONTANA':'MT','NEBRASKA':'NE','NEVADA':'NV','NEW HAMPSHIRE':'NH','NEW JERSEY':'NJ','NEW MEXICO':'NM','NEW YORK':'NY','NORTH CAROLINA':'NC','NORTH DAKOTA':'ND','OHIO':'OH','OKLAHOMA':'OK','OREGON':'OR','PENNSYLVANIA':'PA','RHODE ISLAND':'RI','SOUTH CAROLINA':'SC','SOUTH DAKOTA':'SD','TENNESSEE':'TN','TEXAS':'TX','UTAH':'UT','VERMONT':'VT','VIRGINIA':'VA','WASHINGTON':'WA','WEST VIRGINIA':'WV','WISCONSIN':'WI','WYOMING':'WY','DISTRICT OF COLUMBIA':'DC'}
STATE_ALT='|'.join(sorted((re.escape(x) for x in US_STATES),key=len,reverse=True))
BEFORE_RE=re.compile(rf'\b({STATE_ALT})\b[\s\|,:;\-]{{0,120}}\(?\s*State(?:\s+or\s+other\s+jurisdiction)?\s+of\s+incorporation(?:\s+or\s+organization)?',re.I)
AFTER_RE=re.compile(rf'State(?:\s+or\s+other\s+jurisdiction)?\s+of\s+incorporation(?:\s+or\s+organization)?[\s\|,:;\-\)\(]{{0,120}}\b({STATE_ALT})\b',re.I)
MD_LINK_RE=re.compile(r'\[[^\]]+\]\((https?://(?:www\.)?sec\.gov/Archives/edgar/data/[^\)]+\.html?)\)',re.I)
HTML_LINK_RE=re.compile(r'href=["\']([^"\']+\.html?)["\']',re.I)

def primary_urls(index_url):
 try:text,_=old.get(index_url,timeout=15)
 except Exception:return []
 out=[]
 for line in text.splitlines():
  if not re.search(r'\b10-K\b',line,re.I) or re.search(r'10-K/A',line,re.I):continue
  for u in MD_LINK_RE.findall(line):
   if u not in out:out.append(u)
  for u in HTML_LINK_RE.findall(line):
   if u.startswith('/'):u='https://www.sec.gov'+u
   elif not u.startswith('http'):
    u=index_url.rsplit('/',1)[0]+'/'+u
   if u not in out:out.append(u)
 return out[:3]
def cover_state(text,target):
 cover=text[:30000]
 if target not in old.normalize_name(cover):return None
 for rgx in (BEFORE_RE,AFTER_RE):
  m=rgx.search(cover)
  if m:return US_STATES[m.group(1).upper()]
 return None
def identity_key(r):return (str(r.get('ticker') or '').upper(),str(r.get('securityId') or '').upper())
def main():
 base=json.loads(BASE.read_text());final=json.loads(FINAL.read_text());pit=json.loads(PIT.read_text())
 sf={r['seriesId']:r['filingDate'] for r in pit.get('records',[]) if r.get('seriesId') and r.get('filingDate')}
 resolved=set()
 for h in final.get('rows',[]):
  ids=h.get('identities') or []
  if h.get('classification') in {'US','NON_US'} and len(ids)==1:resolved.add(identity_key(ids[0]))
 pop=[r for r in base.get('identityRows',[]) if r.get('classification')=='UNKNOWN' and identity_key(r) not in resolved]
 pop=sorted(pop,key=lambda r:(str(r.get('ticker') or ''),str(r.get('securityId') or ''),str(r.get('issuer') or '')))
 shard=[r for i,r in enumerate(pop) if i%N==SHARD];rows=[]
 for i,row in enumerate(shard,1):
  cutoff=hdr.cutoff_for(row,sf);target=old.normalize_name(row.get('issuer') or '')
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','occurrenceCount','seriesIds','asOfReportDate']};rec.update({'countryEvidenceCutoff':cutoff,'classification':'UNKNOWN'})
  cands=hdr.candidate_ciks(row,cutoff);rec['candidateCiks']=[c[0] for c in cands]
  if len(cands)==1:
   cik,seed=cands[0]
   try:b=hdr.browse_10k_cik(cik,cutoff)
   except Exception:b={}
   for idx in b.get('archiveUrls',[])[:10]:
    for pu in primary_urls(idx):
     try:text,tr=old.get(pu,timeout=15)
     except Exception:continue
     code=cover_state(text,target)
     if code:
      rec.update({'classification':'US','stateCode':code,'historicalCik':cik,'indexUrl':idx,'primaryDocumentUrl':pu,'transport':tr,'resolutionSource':seed+'_THEN_PIT_10K_COVER'});break
    if rec['classification']=='US':break
  rows.append(rec);print(f'{i}/{len(shard)}',json.dumps(rec),flush=True);time.sleep(.02)
 resolved_rows=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'UNKNOWN-only PIT country attribution from the historical Form 10-K cover page. CIK candidates use the same preregistered deterministic hierarchy as the SEC header-SGML route. A holding is promoted to US only when the historical primary 10-K document published by the legacy cutoff contains the normalized legacy issuer name and a standard Form 10-K State of incorporation field with an explicit US state. Current state, address state, fuzzy matching, returns and ranks are never used.','shardIndex':SHARD,'shardCount':N,'remainingUnknownIdentityCount':len(pop),'shardCountActual':len(rows),'resolvedCount':len(resolved_rows),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved_rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
