#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'
OUT=ROOT/'data/research/sec-ticker-seed-historical-name-validate-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
old=cur.old
NAME_RE=re.compile(r'COMPANY CONFORMED NAME:\s*([^\r\n<]+)',re.I)
STATE_PATTERNS=[
 re.compile(r'STATE-OF-INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),
 re.compile(r'State\s+of\s+Inc(?:orp(?:oration)?)?\.?\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I),
 re.compile(r'State or other jurisdiction of incorporation[^A-Z0-9]{0,80}([A-Z]{2})\b',re.I),
]

def archive_validate(url,target):
 try:text,tr=old.get(url,timeout=12)
 except Exception:return None
 names=[m.strip() for m in NAME_RE.findall(text)]
 nset={old.normalize_name(x) for x in names}
 if target not in nset:return None
 state=None
 for p in STATE_PATTERNS:
  m=p.search(text)
  if m: state=m.group(1).upper();break
 if not state:return None
 return {'stateCode':state,'classification':'US' if state in old.US_CODES else 'NON_US','historicalNames':names[:5],'filingUrl':url,'transport':tr}

def main():
 data=json.loads(SRC.read_text()); unknown=sorted([r for r in data['identityRows'] if r.get('classification')=='UNKNOWN'],key=lambda r:float(r.get('aggregateWeight') or 0),reverse=True)[:50]
 out=[]
 for row in unknown:
  target=old.normalize_name(row['issuer']); rec={k:row.get(k) for k in ['ticker','securityId','issuer','asOfReportDate','aggregateWeight']}; rec['classification']='UNKNOWN'
  seeds=cur.CM.get(str(row['ticker']).upper(),[])
  rec['tickerSeedCandidates']=seeds[:3]
  # Ticker may be reused. Seed only if exactly one current CIK candidate, then validate historical registrant name exactly after legal-suffix normalization.
  ciks=sorted(set(x['cik'] for x in seeds))
  if len(ciks)==1:
   try:
    b=old.browse_cik(ciks[0],row['asOfReportDate']); rec['seedCik']=ciks[0];rec['archiveCount']=len(b.get('archiveUrls',[]))
    for url in b.get('archiveUrls',[])[:16]:
     v=archive_validate(url,target)
     if v:
      rec.update(v);rec['resolutionSource']='CURRENT_TICKER_CIK_HISTORICAL_NAME_VALIDATED';break
   except Exception as e:rec['error']=type(e).__name__
  out.append(rec);print('VALIDATE',json.dumps({k:rec.get(k) for k in ['ticker','issuer','aggregateWeight','classification','stateCode','seedCik','archiveCount']}),flush=True);time.sleep(.08)
 resolved=[r for r in out if r['classification']!='UNKNOWN']
 summary={'purpose':'UNKNOWN-only PIT country pilot. Current ticker is used only as a CIK seed. Classification is accepted only when a filing available by the legacy report date contains a historical COMPANY CONFORMED NAME matching the legacy issuer after fixed legal-suffix normalization, plus filing-time state/country. No current state, returns, or ranks used.','sampleCount':len(out),'resolvedCount':len(resolved),'resolvedWeight':sum(float(r['aggregateWeight']) for r in resolved),'sampleWeight':sum(float(r['aggregateWeight']) for r in out),'rows':out}
 OUT.write_text(json.dumps(summary,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
