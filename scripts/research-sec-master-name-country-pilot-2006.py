#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request,zipfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-master-name-country-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com'}
US={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
STATE_RE=re.compile(r'STATE-OF-INCORPORATION:\s*([A-Z0-9]{2,3})',re.I)

def norm(s):
 s=s.upper().replace('&',' AND ');s=re.sub(r'\b(THE)\b',' ',s);s=re.sub(r'\b(INCORPORATED|INCORPORATION)\b',' INC ',s);s=re.sub(r'\b(CORPORATION)\b',' CORP ',s);s=re.sub(r'\b(COMPANY)\b',' CO ',s);s=re.sub(r'\b(LIMITED)\b',' LTD ',s);return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def issuer_base(s):
 s=re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$','',s,flags=re.I);return norm(s)
def get(url):
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA);return urllib.request.urlopen(req,timeout=20).read(),u
  except Exception: pass
 raise RuntimeError('fetch failed '+url)
def masters():
 rows=[]
 # 2006 only: this transport is already confirmed on the prior legacy-series pilot.
 for y in (2006,):
  for q in (1,2,3,4):
   url=f'https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/master.zip'; b,t=get(url)
   z=zipfile.ZipFile(io.BytesIO(b)); txt=z.read('master.idx').decode('latin1','replace')
   for line in txt.splitlines():
    p=line.split('|')
    if len(p)==5 and p[2] in {'10-K','10-K/A','10-K405'}: rows.append({'cik':p[0],'company':p[1],'form':p[2],'date':p[3],'path':p[4]})
 return rows
def main():
 data=json.loads(SRC.read_text()); unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:50]
 idx=masters(); by={}
 for r in idx: by.setdefault(norm(r['company']),[]).append(r)
 out=[]
 for row in unknown:
  q=issuer_base(row['issuer']); cands=by.get(q,[]); ciks=sorted(set(c['cik'] for c in cands)); rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight']};rec['normalizedIssuer']=q;rec['masterCandidateCiks']=ciks;rec['masterCandidateCount']=len(cands);rec['classification']='UNKNOWN'
  if len(ciks)==1:
   cand=sorted(cands,key=lambda x:x['date'])[0]; url='https://www.sec.gov/Archives/'+cand['path']
   try:
    b,t=get(url); text=b.decode('utf-8','replace');m=STATE_RE.search(text)
    if m:
     code=m.group(1).upper();rec.update({'classification':'US' if code in US else 'NON_US','stateCode':code,'cik':cand['cik'],'filingPath':cand['path'],'transport':t})
   except Exception as e: rec['error']=type(e).__name__
  out.append(rec);print('PILOT',json.dumps(rec),flush=True)
 resolved=[r for r in out if r['classification']!='UNKNOWN']
 summary={'purpose':'PIT country resolver pilot using official 2006 SEC master indexes only: unique exact normalized issuer company-name -> CIK, then historical 10-K SGML STATE-OF-INCORPORATION. No current metadata, returns, or ranks used.','sampleCount':len(out),'uniqueMasterCikCount':sum(len(r['masterCandidateCiks'])==1 for r in out),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r['aggregateWeight']) for r in resolved),'sampleWeight':sum(float(r['aggregateWeight']) for r in out),'rows':out}
 OUT.write_text(json.dumps(summary,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
