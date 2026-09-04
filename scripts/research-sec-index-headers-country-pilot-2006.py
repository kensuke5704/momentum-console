#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-index-headers-country-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
old=cur.old
ENTITY_RE=re.compile(r'(?m)^\s*(?:[-*]\s*)?([^\n\r|]{2,140}?)\s+\((Filer|Issuer|Reporting)\)\s+CIK:\s*(?:\*\*)?(?:\[)?(\d{10})',re.I)

def acc_from_dir(d):
 d=''.join(ch for ch in d if ch.isdigit())
 if len(d)!=18:return None
 return f'{d[:10]}-{d[10:12]}-{d[12:]}'
def filing_index_urls(archive_url):
 m=re.search(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/',archive_url,re.I)
 if not m:return []
 cik,ad=m.group(1),m.group(2);acc=acc_from_dir(ad)
 if not acc:return []
 base=f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index'
 out=[]
 if re.search(r'-index\.html?$',archive_url,re.I):out.append(archive_url)
 out.extend([base+'.htm',base+'.html'])
 return list(dict.fromkeys(out))
def entity_state(target,cik,text):
 matches=list(ENTITY_RE.finditer(text));nt=old.normalize_name(target);zcik=str(cik).zfill(10)
 for i,m in enumerate(matches):
  name,role,mcik=m.group(1).strip(),m.group(2).upper(),m.group(3).zfill(10)
  if mcik!=zcik or old.normalize_name(name)!=nt:continue
  end=matches[i+1].start() if i+1<len(matches) else min(len(text),m.end()+2500)
  block=text[m.start():end]
  states=list(dict.fromkeys(x.upper() for x in old.STATE_RE.findall(block)))
  if states:return states[0],name,role
 return None,None,None

def main():
 data=json.loads(SRC.read_text())
 unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:10]
 results=[]
 for row in unknown:
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
  cm=cur.CM.get((row.get('ticker') or '').upper(),[]);target=old.normalize_name(row.get('issuer') or '')
  exact=[x for x in cm if x.get('normalizedTitle')==target]
  if len(exact)==1:
   cik=exact[0]['cik'];rec['seedCik']=cik;rec['seedSource']='CURRENT_TICKER_EXACT_NAME'
   try:
    b=old.browse_cik(cik,row['asOfReportDate']);rec['archiveCount']=len(b.get('archiveUrls',[]));seen=[]
    for au in b.get('archiveUrls',[])[:16]:
     for iu in filing_index_urls(au):
      if iu in seen:continue
      seen.append(iu)
      try:
       text,tr=old.get(iu,timeout=12);st,name,role=entity_state(row['issuer'],cik,text)
       rec.setdefault('attempts',[]).append({'indexUrl':iu,'transport':tr,'entityName':name,'entityRole':role,'stateCode':st})
       if st:
        rec.update({'classification':'US' if st in old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_FILING_INDEX_ENTITY_STATE','indexUrl':iu,'historicalEntityName':name,'historicalEntityRole':role});break
      except Exception as e:rec.setdefault('attempts',[]).append({'indexUrl':iu,'error':type(e).__name__})
      time.sleep(.05)
     if rec['classification']!='UNKNOWN':break
   except Exception as e:rec['browseError']=type(e).__name__
  results.append(rec);print('INDEX',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','seedCik','archiveCount','classification','stateCode','resolutionSource','indexUrl']}),flush=True)
 resolved=[r for r in results if r['classification']!='UNKNOWN']
 out={'purpose':'Fast top-10 UNKNOWN PIT country pilot. Current ticker metadata is used only as an exact-normalized-name CIK seed. Classification requires a historical SEC filing index page available by the legacy report date, the same seeded CIK, a normalized historical entity name matching the legacy issuer, and that entity block State of Incorp. No current state, returns, ranks, or strategy outcomes are used.','sampleCount':len(results),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in results),'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
