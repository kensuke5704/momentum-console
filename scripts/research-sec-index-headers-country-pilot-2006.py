#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,io,json,re,time,urllib.request,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-index-headers-country-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
old=cur.old
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,application/zip,*/*','Accept-Encoding':'identity'}
ENTITY_RE=re.compile(r'(?m)^\s*(?:[-*]\s*)?([^\n\r|]{2,140}?)\s+\((Filer|Issuer|Reporting)\)\s+CIK:\s*(?:\*\*)?(?:\[)?(\d{10})',re.I)
JURIS_RE=re.compile(r'\s*/[A-Z0-9]{2,3}/\s*$',re.I)

def normalize_company(s):
 return old.normalize_name(JURIS_RE.sub('',s or ''))

def get_master(year,q):
 base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
 zurl=base+'/master.zip'
 try:
  req=urllib.request.Request(zurl,headers=UA)
  with urllib.request.urlopen(req,timeout=45) as r:data=r.read(20_000_000)
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   name=next(n for n in z.namelist() if n.lower().endswith('master.idx'))
   return z.read(name).decode('latin-1','replace'),zurl
 except Exception as ze:
  text,tr=old.get(base+'/master.idx',timeout=60)
  return text,tr+' | zip_error='+type(ze).__name__

def load_master(years):
 rows=[];transports={}
 for year in years:
  for q in range(1,5):
   text,tr=get_master(year,q);transports[f'{year}Q{q}']=tr
   for line in text.splitlines():
    p=line.split('|')
    if len(p)<5 or not p[0].strip().isdigit():continue
    cik,company,form,date,filename=[x.strip() for x in p[:5]]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):continue
    rows.append({'cik':cik.zfill(10),'company':company,'normalizedCompany':normalize_company(company),'form':form.upper(),'dateFiled':date,'filename':filename})
 return rows,transports

def accession_parts(filename):
 m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',filename,re.I)
 if not m:return None
 cik=str(int(m.group(1)));acc=m.group(2);ad=acc.replace('-','')
 return cik,acc,ad

def filing_index_urls_from_filename(filename):
 parts=accession_parts(filename)
 if not parts:return []
 cik,acc,ad=parts;base=f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index'
 return [base+'.htm',base+'.html']

def entity_state(target,cik,text):
 matches=list(ENTITY_RE.finditer(text));nt=normalize_company(target);zcik=str(cik).zfill(10)
 for i,m in enumerate(matches):
  name,role,mcik=m.group(1).strip(),m.group(2).upper(),m.group(3).zfill(10)
  if mcik!=zcik or normalize_company(name)!=nt:continue
  end=matches[i+1].start() if i+1<len(matches) else min(len(text),m.end()+3000)
  block=text[m.start():end]
  states=list(dict.fromkeys(x.upper() for x in old.STATE_RE.findall(block)))
  if states:return states[0],name,role
 return None,None,None

def resolve_from_rows(row,master_rows):
 target=normalize_company(row.get('issuer') or '');dateb=row['asOfReportDate'];rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
 exact=[r for r in master_rows if r['dateFiled']<=dateb and r['normalizedCompany']==target]
 by_cik=defaultdict(list)
 for r in exact:by_cik[r['cik']].append(r)
 seed=None;source=None
 if len(by_cik)==1:
  seed=next(iter(by_cik));source='HISTORICAL_MASTER_EXACT_NAME'
  candidates=sorted(by_cik[seed],key=lambda x:(x['dateFiled'],x['filename']),reverse=True)
 else:
  cm=cur.CM.get((row.get('ticker') or '').upper(),[]);current_exact=[x for x in cm if normalize_company(x.get('title') or '')==target]
  if len(current_exact)==1:
   seed=current_exact[0]['cik'];source='CURRENT_TICKER_EXACT_NAME'
   candidates=sorted([r for r in master_rows if r['dateFiled']<=dateb and r['cik']==seed],key=lambda x:(x['dateFiled'],x['filename']),reverse=True)
  else:candidates=[]
 rec['historicalExactCikCount']=len(by_cik);rec['historicalExactCiks']=sorted(by_cik)[:6]
 if not seed:return rec
 rec['seedCik']=seed;rec['seedSource']=source;rec['filingCandidateCount']=len(candidates)
 seen=set()
 for fr in candidates[:12]:
  for iu in filing_index_urls_from_filename(fr['filename']):
   if iu in seen:continue
   seen.add(iu)
   try:
    text,tr=old.get(iu,timeout=10);st,name,role=entity_state(row['issuer'],seed,text)
    rec.setdefault('attempts',[]).append({'form':fr['form'],'dateFiled':fr['dateFiled'],'indexUrl':iu,'transport':tr,'entityName':name,'entityRole':role,'stateCode':st})
    if st:
     rec.update({'classification':'US' if st in old.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_FILING_INDEX_ENTITY_STATE','indexUrl':iu,'historicalEntityName':name,'historicalEntityRole':role,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled']});return rec
   except Exception as e:rec.setdefault('attempts',[]).append({'form':fr['form'],'dateFiled':fr['dateFiled'],'indexUrl':iu,'error':type(e).__name__})
   time.sleep(.03)
 return rec

def main():
 data=json.loads(SRC.read_text())
 unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:10]
 years=sorted({int(r['asOfReportDate'][:4]) for r in unknown})
 master_rows,master_transports=load_master(years)
 print('MASTER',json.dumps({'years':years,'rows':len(master_rows),'transports':master_transports}),flush=True)
 results=[]
 for row in unknown:
  rec=resolve_from_rows(row,master_rows);results.append(rec);print('INDEX',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','historicalExactCikCount','seedCik','seedSource','filingCandidateCount','classification','stateCode','resolutionSource','evidenceForm','evidenceDateFiled']}),flush=True)
 resolved=[r for r in results if r['classification']!='UNKNOWN']
 out={'purpose':'Fast top-10 UNKNOWN PIT country pilot using official historical SEC quarterly master indexes from the report year to resolve filing-time company name -> CIK -> filing path directly, avoiding browse-edgar transport. Historical exact normalized company name is preferred; current ticker metadata is only a fallback exact-name CIK seed. Classification still requires a historical filing index entity block with the same CIK, matching normalized issuer name, and State of Incorp. No current state, returns, ranks, or strategy outcomes are used.','masterYears':years,'masterIndexTransports':master_transports,'masterRowCount':len(master_rows),'sampleCount':len(results),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in results),'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('results','masterIndexTransports')}),flush=True)
if __name__=='__main__':main()
