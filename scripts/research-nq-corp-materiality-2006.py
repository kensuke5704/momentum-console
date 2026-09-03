#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INP=ROOT/'data/research/nq-pit-holdings-2006-ec-filtered.json'
OUT=ROOT/'data/research/nq-corp-materiality-2006.json'
REGISTERED_FUND=re.compile(r'\b(?:ETF|EXCHANGE[ -]TRADED|MUTUAL FUND|INDEX FUND|INVESTMENT FUND|INCOME FUND|EQUITY FUND|MONEY MARKET FUND)\b',re.I)
PRIVATE_FUND=re.compile(r'\b(?:HEDGE FUND|PRIVATE EQUITY FUND|VENTURE FUND)\b',re.I)
SOVEREIGN_GOV=re.compile(r'\b(?:UNITED STATES TREASURY|U\.S\. TREASURY|GOVERNMENT OF|REPUBLIC OF|KINGDOM OF)\b',re.I)
MUNICIPAL=re.compile(r'\b(?:CITY OF|COUNTY OF|MUNICIPAL)\b',re.I)
def main():
 d=json.loads(INP.read_text());records=d.get('records',d.get('series',[]));totalc=0;totalw=0.0;cand=[]
 for r in records:
  for h in r.get('holdings',[]):
   desc=h.get('description') or h.get('issuerName') or '';w=float(h.get('weight') or 0);totalc+=1;totalw+=w;cats=[]
   if REGISTERED_FUND.search(desc):cats.append('REGISTERED_FUND_POSITIVE_NAME')
   if PRIVATE_FUND.search(desc):cats.append('PRIVATE_FUND_POSITIVE_NAME')
   if SOVEREIGN_GOV.search(desc):cats.append('SOVEREIGN_OR_GOV_POSITIVE_NAME')
   if MUNICIPAL.search(desc):cats.append('MUNICIPAL_POSITIVE_NAME')
   if cats:cand.append({'seriesId':r.get('seriesId'),'seriesName':r.get('seriesName'),'description':desc,'weight':w,'signals':cats})
 pw=sum(x['weight'] for x in cand);out={'purpose':'Materiality diagnostic for N-PORT ISSUER_TYPE=CORP bridge on 2006 legacy N-Q holdings already restricted to explicit COMMON_EQUITY sections. Identify only positive textual evidence for issuer categories N-PORT separates from corporate. Generic Trust/LP/legal-form strings are not classified. No returns or Universe ranks used.','holdingCount':totalc,'holdingWeight':totalw,'positiveNonCorpNameCount':len(cand),'positiveNonCorpNameCountRate':len(cand)/totalc if totalc else None,'positiveNonCorpNameWeight':pw,'positiveNonCorpNameWeightRate':pw/totalw if totalw else None,'candidates':cand}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='candidates'}),flush=True);print('CANDIDATES',json.dumps(cand),flush=True)
if __name__=='__main__':main()
# trigger 2026-09-03
