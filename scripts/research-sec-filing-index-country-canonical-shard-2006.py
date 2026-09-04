#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
SHARD_INDEX=int(os.environ.get('SHARD_INDEX','0'));SHARD_COUNT=int(os.environ.get('SHARD_COUNT','12'))
OUT=ROOT/f'data/research/sec-filing-index-country-canonical-shard-{SHARD_INDEX:02d}-of-{SHARD_COUNT:02d}-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
STATE_RE=re.compile(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I)
ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)
CORP_EQ={'CORPORATION':'CORP','CORP':'CORP','INCORPORATED':'INC','INC':'INC','COMPANY':'CO','CO':'CO','LIMITED':'LTD','LTD':'LTD'}
def canon(s:str)->str:
 s=re.sub(r'\s*\([a-z]\)\s*$',' ',str(s),flags=re.I).upper().replace('&',' AND ')
 s=re.sub(r'[^A-Z0-9]+',' ',s);toks=[CORP_EQ.get(t,t) for t in s.split()]
 if toks and toks[0]=='THE':toks=toks[1:]
 return ' '.join(toks)
def index_urls(doc_url:str):
 m=ARCH_RE.search(doc_url)
 if not m:return []
 cik,compact=m.group(1),m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}'
 base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}-index'
 return [base+'.htm',base+'.html']
def main():
 data=json.loads(SRC.read_text());all_unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:(str(r.get('ticker') or ''),str(r.get('securityId') or '')))
 unknown=[r for i,r in enumerate(all_unknown) if i%SHARD_COUNT==SHARD_INDEX];rows=[]
 for row in unknown:
  ticker=str(row.get('ticker') or '').upper();issuer=row.get('issuer') or '';dateb=row.get('asOfReportDate') or '2006-12-31';target=canon(issuer)
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN';rec['seedCount']=0
  seeds=[x for x in cur.CM.get(ticker,[]) if canon(x.get('title') or '')==target];rec['seedCount']=len(seeds)
  if len(seeds)==1:
   seed=seeds[0]
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
     code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'currentTitle':seed.get('title'),'indexUrl':iu,'transport':tr,'resolutionSource':'CURRENT_TICKER_CANONICAL_CORP_SUFFIX_CIK_THEN_PIT_FILING_INDEX'})
     break
    if rec['classification']!='UNKNOWN':break
  rows.append(rec);print('ROW',json.dumps(rec),flush=True);time.sleep(.02)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'Sharded full UNKNOWN PIT country resolution under the frozen canonical corporate-designator seed rule. Current ticker metadata seeds CIK only; final classification comes only from historical filing-index State of Incorp. No current state, fuzzy matching, returns, or ranks.','shardIndex':SHARD_INDEX,'shardCount':SHARD_COUNT,'totalUnknownPopulation':len(all_unknown),'sampleCount':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
