#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-complete-submission-country-pilot-2006.json'
SPEC=importlib.util.spec_from_file_location('base',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
base=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(base)
SGML_STATE_RE=re.compile(r'<STATE-OF-INCORPORATION>\s*([A-Z0-9]{2,3})',re.I)
PLAIN_STATE_RE=re.compile(r'STATE-OF-INCORPORATION:\s*([A-Z0-9]{2,3})',re.I)
NAME_RE=re.compile(r'(?:<COMPANY-CONFORMED-NAME>|COMPANY CONFORMED NAME:)\s*([^\r\n<]+)',re.I)
ACC_DIR_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)

def norm(s:str)->str:
 return base.old.normalize_name(s)

def complete_url(doc_url:str)->str|None:
 m=ACC_DIR_RE.search(doc_url)
 if not m:return None
 cik,compact=m.group(1),m.group(2)
 acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}'
 return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{acc}.txt'

def main():
 data=json.loads(SRC.read_text())
 unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:30]
 cm=base.CM
 rows=[]
 for row in unknown:
  ticker=str(row.get('ticker') or '').upper(); issuer=row.get('issuer') or ''; dateb=row.get('asOfReportDate') or '2006-12-31'; target=norm(issuer)
  rec={k:row.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','asOfReportDate']};rec['classification']='UNKNOWN'
  seeds=cm.get(ticker,[])
  # ticker is seed only; current title is not country evidence.
  for seed in seeds[:3]:
   try:b=base.old.browse_cik(seed['cik'],dateb)
   except Exception:continue
   for doc in b.get('archiveUrls',[])[:16]:
    cu=complete_url(doc)
    if not cu:continue
    try:text,tr=base.old.get(cu,timeout=18)
    except Exception:continue
    names=[x.strip() for x in NAME_RE.findall(text)]
    if not names or not any(norm(x)==target for x in names):continue
    sm=SGML_STATE_RE.search(text) or PLAIN_STATE_RE.search(text)
    if not sm:continue
    code=sm.group(1).upper()
    rec.update({'classification':'US' if code in base.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'completeSubmissionUrl':cu,'transport':tr,'historicalNames':names[:3]})
    break
   if rec['classification']!='UNKNOWN':break
  rows.append(rec);print('PILOT',json.dumps(rec),flush=True);time.sleep(.08)
 resolved=[r for r in rows if r['classification']!='UNKNOWN']
 out={'purpose':'UNKNOWN-only PIT country pilot using deterministic complete-submission .txt derived from historical archive URLs. Current ticker is CIK seed only; classification requires historical COMPANY CONFORMED NAME exact normalized match and filing-time STATE-OF-INCORPORATION. No current state, returns, or ranks used.','sampleCount':len(rows),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in resolved),'sampleWeight':sum(float(r.get('aggregateWeight') or 0) for r in rows),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
