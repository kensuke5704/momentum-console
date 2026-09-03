#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('h',ROOT/'scripts'/'research-production-jan2020-hybrid-shadow.py')
h=importlib.util.module_from_spec(S);S.loader.exec_module(h)
OUT=ROOT/'data/research/production-jan2020-substitution-decomposition.json'
EXACT={'S000057700':'0001752724-20-012434','S000063326':'0001752724-20-013847','S000061208':'0001145549-20-003103'}

def nport_source(filings,sid):
 f=next(x for x in filings if x.get('seriesId')==sid and x.get('accession')==EXACT[sid])
 return {'seriesId':sid,'seriesName':f['seriesName'],'filingDate':f['filingDate'],'reportDate':f['reportDate'],'sourceKind':'NPORT_EXACT','holdings':[{'symbol':x['symbol'],'issuerName':x.get('issuerName'),'weight':float(x['weight'])} for x in f['holdings']]}
def legacy_sources(filings,legacy):
 master=h.identity_master(filings);out={};maps={}
 for rec in legacy['records']:
  merged={};mc=mw=0;tw=sum(x['weight'] for x in rec['holdings'])
  for x in rec['holdings']:
   sym=h.resolve(master,rec['seriesId'],x['description'])
   if not sym:continue
   mc+=1;mw+=x['weight'];r=merged.setdefault(sym,{'symbol':sym,'issuerName':x['description'],'weight':0.0});r['weight']+=x['weight']
  out[rec['seriesId']]={'seriesId':rec['seriesId'],'seriesName':rec['seriesName'],'filingDate':rec['filingDate'],'reportDate':rec['reportDate'],'sourceKind':'LEGACY_RECONSTRUCTED','holdings':list(merged.values())}
  maps[rec['seriesId']]={'mappedCount':mc,'legacyCount':len(rec['holdings']),'mappedWeight':mw,'legacyWeight':tw}
 return out,maps
def eval_case(name,sources,prod):
 kept=[s for s in sources if h.eligible(s)];rows=h.score(kept);cand=[x['symbol'] for x in rows]
 common=set(prod)&set(cand);pr={s:i+1 for i,s in enumerate(prod)};cr={s:i+1 for i,s in enumerate(cand)}
 return {'case':name,'sources':[{'seriesId':s['seriesId'],'sourceKind':s['sourceKind'],'eligible':h.eligible(s)} for s in sources],'candidateUniverse':cand,'topKOverlap':len(common)/len(prod),'commonNames':len(common),'spearmanCommonRanks':h.corr([pr[s] for s in common],[cr[s] for s in common]),'top2Retention':sum(s in set(cand) for s in prod[:2])/2,'missingProduction':sorted(set(prod)-set(cand)),'extraCandidate':sorted(set(cand)-set(prod))}
def main():
 with gzip.open(h.BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;legacy=json.loads(h.LEGACY.read_text());ls,maps=legacy_sources(filings,legacy)
 hist=h.history_month(json.loads(h.HISTORY.read_text()));prod=[x['symbol'] for x in hist['symbols']]
 exact={sid:nport_source(filings,sid) for sid in EXACT}
 cases=[
  eval_case('PPTY_ONLY_91D',[exact['S000057700'],exact['S000063326'],ls['S000061208']],prod),
  eval_case('LRGE_ONLY_274D',[ls['S000057700'],exact['S000063326'],exact['S000061208']],prod),
  eval_case('BOTH_LEGACY',[ls['S000057700'],exact['S000063326'],ls['S000061208']],prod),
 ]
 out={'purpose':'Outcome decomposition after parser/mapping rules were frozen: replace only the 91-day PPTY source, only the 274-day LRGE source, or both. This does not change any parser, mapping, threshold, or source-selection rule.','productionUniverse':prod,'legacyMapping':maps,'cases':cases}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 for c in cases:print('CASE',json.dumps(c),flush=True)
if __name__=='__main__':main()
