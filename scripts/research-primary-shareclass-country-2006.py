#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ADD=ROOT/'data/research/nq-npx-primary-shareclass-mapping-2006.json';COUNTRY=ROOT/'data/research/country-full-coverage-canonical-merge-2006.json';OUT=ROOT/'data/research/primary-shareclass-country-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py');cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
STATE_RE=re.compile(r'(?:State\s+of\s+Incorp\.?|STATE\s+OF\s+INCORPORATION)\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I);ARCH_RE=re.compile(r'/Archives/edgar/data/(\d+)/(\d{18})/',re.I)
CORP_EQ={'CORPORATION':'CORP','CORP':'CORP','INCORPORATED':'INC','INC':'INC','COMPANY':'CO','CO':'CO','LIMITED':'LTD','LTD':'LTD'}
def canon(s):
 s=re.sub(r'\s*\([a-z]\)\s*$',' ',str(s),flags=re.I).upper().replace('&',' AND ');s=re.sub(r'[^A-Z0-9]+',' ',s);t=[CORP_EQ.get(x,x) for x in s.split()]
 if t and t[0]=='THE':t=t[1:]
 return ' '.join(t)
def idx_urls(doc):
 m=ARCH_RE.search(doc)
 if not m:return []
 compact=m.group(2);acc=f'{compact[:10]}-{compact[10:12]}-{compact[12:]}';base=f'https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/{compact}/{acc}-index';return [base+'.htm',base+'.html']
def main():
 add=json.loads(ADD.read_text());country=json.loads(COUNTRY.read_text());known={(r['ticker'],r['securityId']):r for r in country['identityRows']};grp=defaultdict(list)
 for h in add['additions']:grp[(h['ticker'],h['securityId'])].append(h)
 rows=[]
 for k,hs in grp.items():
  ticker,sid=k;desc=hs[0]['description'];dateb=min(str(h.get('reportDate') or '2006-12-31') for h in hs);rec={'ticker':ticker,'securityId':sid,'issuer':desc,'asOfReportDate':dateb,'holdingCount':len(hs),'aggregateWeight':sum(float(h['weight']) for h in hs),'classification':'UNKNOWN'}
  prior=known.get(k)
  if prior and prior.get('classification') in {'US','NON_US'}:rec.update({'classification':prior['classification'],'resolutionSource':'REUSED_EXISTING_PIT_IDENTITY_CLASSIFICATION','stateCode':prior.get('stateCode')})
  elif re.search(r'\bADR\b|\bGDR\b|American Depositary|Global Depositary',desc,re.I):rec.update({'classification':'NON_US','resolutionSource':'EXPLICIT_ADR_GDR'})
  elif sid and sid[0].isalpha():rec.update({'classification':'NON_US','resolutionSource':'CINS_NON_US'})
  else:
   seeds=[x for x in cur.CM.get(ticker.upper(),[]) if canon(x.get('title') or '')==canon(desc)]
   if len(seeds)==1:
    seed=seeds[0]
    try:b=cur.old.browse_cik(seed['cik'],dateb)
    except Exception:b={}
    done=False
    for doc in b.get('archiveUrls',[])[:16]:
     for iu in idx_urls(doc):
      try:text,tr=cur.old.get(iu,timeout=18)
      except Exception:continue
      sm=STATE_RE.search(text)
      if not sm:continue
      code=sm.group(1).upper();rec.update({'classification':'US' if code in cur.old.US_CODES else 'NON_US','stateCode':code,'seedCik':seed['cik'],'currentTitle':seed.get('title'),'indexUrl':iu,'transport':tr,'resolutionSource':'CURRENT_TICKER_CANONICAL_CIK_THEN_PIT_FILING_INDEX'});done=True;break
     if done:break
  rows.append(rec);print('ROW',json.dumps(rec),flush=True);time.sleep(.03)
 resolved=[r for r in rows if r['classification']!='UNKNOWN'];out={'purpose':'PIT country attribution for the preregistered primary share-class unique-exact mapping additions. Reuse prior PIT identity classifications when available; otherwise explicit ADR/GDR, CINS non-US, then current-ticker CIK seed with historical filing-index State of Incorp. Current state, fuzzy matching, ranks, and returns are prohibited.','identityCount':len(rows),'holdingCount':len(add['additions']),'holdingWeight':sum(float(x['weight']) for x in add['additions']),'resolvedIdentityCount':len(resolved),'resolvedHoldingCount':sum(r['holdingCount'] for r in resolved),'resolvedHoldingWeight':sum(r['aggregateWeight'] for r in resolved),'rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
