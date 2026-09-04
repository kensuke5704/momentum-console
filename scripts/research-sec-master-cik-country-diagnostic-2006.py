#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,io,json,re,urllib.request,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-master-cik-country-diagnostic-2006.json'
SPEC=importlib.util.spec_from_file_location('old',ROOT/'scripts'/'research-sec-us-attribution-sample-2006.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,application/zip,*/*','Accept-Encoding':'identity'}
JURIS_RE=re.compile(r'\s*/[A-Z0-9]{2,3}/?\s*$',re.I)
ISSUER_FORMS={'10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','DEF 14A','DEFA14A','PRE 14A','11-K','S-8','S-8 POS'}

def norm(s):return old.normalize_name(JURIS_RE.sub('',s or ''))
def master(q):
 url=f'https://www.sec.gov/Archives/edgar/full-index/2005/QTR{q}/master.zip'
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=45) as r:data=r.read(20_000_000)
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  name=next(n for n in z.namelist() if n.lower().endswith('master.idx'))
  return z.read(name).decode('latin-1','replace')
def is_structural_prefix(a,b):
 if min(len(a),len(b))<8:return False
 short,long=(a,b) if len(a)<=len(b) else (b,a)
 return long==short or long.startswith(short+' ')
def group(rows,target,mode):
 by=defaultdict(list)
 for r in rows:
  ok=r['normalizedCompany']==target if mode=='exact' else is_structural_prefix(r['normalizedCompany'],target)
  if ok:by[r['cik']].append(r)
 return by
def main():
 rows=[]
 for q in range(1,5):
  text=master(q)
  for line in text.splitlines():
   p=line.split('|')
   if len(p)<5 or not p[0].strip().isdigit():continue
   cik,company,form,date,filename=[x.strip() for x in p[:5]];form=form.upper()
   if form in ISSUER_FORMS and re.fullmatch(r'2005-\d{2}-\d{2}',date):rows.append({'cik':cik.zfill(10),'company':company,'normalizedCompany':norm(company),'form':form,'dateFiled':date,'filename':filename})
 data=json.loads(SRC.read_text());unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:10]
 results=[]
 for row in unknown:
  target=norm(row['issuer']);eligible=[r for r in rows if r['dateFiled']<=row['asOfReportDate']];exact=group(eligible,target,'exact');prefix=group(eligible,target,'prefix')
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['exactCikCount']=len(exact);rec['exactCiks']=sorted(exact);rec['structuralPrefixCikCount']=len(prefix);rec['structuralPrefixCiks']=sorted(prefix)
  selected=None;source=None
  if len(exact)==1:selected=exact;source='HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME'
  elif not exact and len(prefix)==1:selected=prefix;source='HISTORICAL_MASTER_ISSUER_FORM_UNIQUE_PREFIX'
  if selected:
   cik=next(iter(selected));cand=sorted(selected[cik],key=lambda x:(x['dateFiled'],x['filename']),reverse=True);rec.update({'seedCik':cik,'seedSource':source,'filingCount':len(cand),'historicalNames':sorted({x['company'] for x in cand})[:8],'latestFilings':cand[:5]})
  results.append(rec);print('CIK',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','exactCikCount','structuralPrefixCikCount','seedCik','seedSource','filingCount','historicalNames']}),flush=True)
 resolved=[r for r in results if r.get('seedCik')]
 out={'purpose':'Identity-only diagnostic on high-weight remaining UNKNOWN issuers. Official 2005 SEC quarterly master indexes are restricted to issuer-bearing periodic/current/proxy forms before CIK seeding. Exact normalized historical company name is preferred; only when exact has zero candidates is a long token-boundary structural prefix accepted, and only when it resolves to exactly one CIK. SEC trailing jurisdiction annotations are removed. No filing state, current ticker state, holdings ranks, or returns are used.','issuerForms':sorted(ISSUER_FORMS),'masterIssuerFormRowCount':len(rows),'sampleCount':len(results),'uniqueCikSeedCount':len(resolved),'uniqueCikSeedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in results),'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('results','issuerForms')}),flush=True)
if __name__=='__main__':main()
