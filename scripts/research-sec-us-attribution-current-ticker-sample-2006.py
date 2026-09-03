#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)
old.OUT=ROOT/'data/research/sec-us-attribution-current-ticker-sample-2006.json'

def current_map():
 text,tr=old.get('https://www.sec.gov/files/company_tickers.json',timeout=30)
 rows=[]
 try:
  obj=json.loads(text);rows=list(obj.values()) if isinstance(obj,dict) else obj
 except Exception:
  # r.jina may wrap JSON as text; recover only explicit SEC object fields.
  for m in re.finditer(r'"cik_str"\s*:\s*(\d+).*?"ticker"\s*:\s*"([^"]+)".*?"title"\s*:\s*"([^"]+)"',text,re.S):
   rows.append({'cik_str':int(m.group(1)),'ticker':m.group(2),'title':m.group(3)})
 out={}
 for r in rows:
  t=str(r.get('ticker') or '').upper().strip();c=str(r.get('cik_str') or '').zfill(10);title=str(r.get('title') or '')
  if t and c.strip('0'):out.setdefault(t,[]).append({'cik':c,'title':title,'normalizedTitle':old.normalize_name(title)})
 print('CURRENT_MAP',json.dumps({'transport':tr,'rows':len(rows),'tickers':len(out)}),flush=True)
 return out
CM=current_map()

def resolve(row):
 ticker,issuer,dateb=row['ticker'],row['issuer'],row['asOfReportDate'];target=old.normalize_name(issuer);out={**row}
 cm=CM.get(ticker.upper(),[])
 exact=[x for x in cm if x['normalizedTitle']==target]
 if len(exact)==1:
  x=exact[0]
  try:
   b=old.browse_cik(x['cik'],dateb)
   # Current ticker table is used only to seed a CIK. Require actual filing archives by the PIT date.
   if b.get('archiveUrls'):
    state,attempts,errors=old.state_from_archives(b['archiveUrls'])
    out.update({'seedSource':'CURRENT_TICKER_EXACT_NAME','seedCik':x['cik'],'currentTitle':x['title'],'archiveCount':len(b['archiveUrls']),'filingAttempts':attempts})
    if errors:out['transportErrors']=errors
    if state:
     out['stateCode']=state;out['classification']='US' if state in old.US_CODES else 'NON_US';out['resolutionSource']='CURRENT_TICKER_CIK_THEN_PIT_FILING';return out
  except Exception as e:out['currentTickerError']=type(e).__name__
 # Conservative fallback to the previously fixed PIT resolver.
 base=old.resolve_security(row);base['currentTickerSeedCandidates']=cm[:3]
 return base

def main():
 mapping=json.loads(old.MAPPING.read_text());ids={}
 for d in mapping.get('details',[]):
  if d.get('status')!='MATCHED_UNIQUE' or len(d.get('identities',[]))!=1:continue
  ident=d['identities'][0];key=(ident['ticker'],ident['securityId']);cand={'ticker':ident['ticker'],'securityId':ident['securityId'],'issuer':d['description'],'asOfReportDate':d['reportDate']}
  if key not in ids or cand['asOfReportDate']<ids[key]['asOfReportDate']:ids[key]=cand
 pop=sorted(ids.values(),key=lambda x:(x['ticker'],x['securityId'],x['issuer']));n=min(old.SAMPLE_N,len(pop));pos=sorted(set(min(len(pop)-1,(i*len(pop))//n) for i in range(n)));sample=[pop[i] for i in pos]
 results=[]
 for i,row in enumerate(sample,1):
  r=resolve(row);results.append(r);print(f'{i}/{len(sample)}',json.dumps(r),flush=True);time.sleep(.12)
 counts={k:sum(1 for r in results if r.get('classification')==k) for k in ['US','NON_US','UNKNOWN']}
 out={'year':2006,'purpose':'Improve deterministic PIT US-country attribution coverage. Current SEC ticker metadata seeds CIK only when ticker and normalized issuer name match uniquely; classification still requires a historical filing available by the N-Q report date and its filing-time state/country code. No current state is used.','sampleRule':'Same fixed 24 equal-quantile identity positions as prior sample.','uniqueIdentityPopulation':len(pop),'sampleCount':len(results),'classificationCounts':counts,'resolvedRate':(counts['US']+counts['NON_US'])/len(results),'results':results}
 old.OUT.parent.mkdir(parents=True,exist_ok=True);old.OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
