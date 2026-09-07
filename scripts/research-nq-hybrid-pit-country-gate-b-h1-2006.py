#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,math,os,re,statistics
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data/research'
MAPPING=D/'nq-hybrid-structural-mapping-h1-2006.json';NPX=D/'npx-security-master-2006.json'
BASE=D/'sec-submission-header-country-full-merged-2006.json';STRUCT=D/'structural-new-matches-submission-header-country-2006.json'
SHARDS=D/'hybrid-country-shards';COUNTRY_OUT=D/'nq-hybrid-country-pit-h1-2006.json';GATE_OUT=D/'nq-hybrid-gate-b-h1-2006.json'
CATALOG_SHA='e2405277fe03a4208e163a43d724fd7364e139ad229caa70251b151f1d53b801'
RECEIPT=re.compile(r'\b(?:ADR|GDR|ADS|AMERICAN\s+DEPOSITARY|GLOBAL\s+DEPOSITARY|DEPOSITARY\s+RECEIPT)S?\b',re.I)
NONCORP=[('REGISTERED_FUND',re.compile(r'\b(?:ETF|EXCHANGE[ -]TRADED|MUTUAL FUND|INDEX FUND|INVESTMENT FUND|INCOME FUND|EQUITY FUND|MONEY MARKET FUND)\b',re.I)),('PRIVATE_FUND',re.compile(r'\b(?:HEDGE FUND|PRIVATE EQUITY FUND|VENTURE FUND)\b',re.I)),('SOV_GOV',re.compile(r'\b(?:UNITED STATES TREASURY|U\.S\. TREASURY|GOVERNMENT OF|REPUBLIC OF|KINGDOM OF)\b',re.I)),('MUNICIPAL',re.compile(r'\b(?:CITY OF|COUNTY OF|MUNICIPAL)\b',re.I))]
STRUCTURED=re.compile(r'\b(2x|3x|ultra|bull|bear|inverse|short|covered call|option income|premium income|buffer|defined outcome|bond|fixed income|treasury|municipal|income|dividend|allocation)\b',re.I)
BROAD=re.compile(r'\b(s&p 500|total market|russell 1000|russell 2000|nasdaq-100|nasdaq 100|dow jones|large cap blend|mid cap blend|small cap blend)\b',re.I)
def loadmod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def ik(t,s):return ((t or '').strip().upper(),(s or '').strip().upper() or None)
def cins(s):
 s=(s or '').strip().upper();return len(s)==9 and s[0].isalpha() and s[0]!='U'
def noncorp(desc):
 t=str(desc or '');return [n for n,p in NONCORP if p.search(t)]
def frozen(base,struct):
 e=defaultdict(list)
 for src,rows in [('BASE',base.get('identityRows',[])),('STRUCT',struct.get('rows',[]))]:
  for r in rows:
   if r.get('classification') in {'US','NON_US'} and r.get('evidenceDateFiled'):
    e[ik(r.get('ticker'),r.get('securityId'))].append({'classification':r['classification'],'source':src,'resolutionSource':r.get('resolutionSource'),'evidenceDateFiled':r['evidenceDateFiled'],'stateCode':r.get('stateCode')})
 return e
def static_country(h,signal,e):
 x=h.get('legacyCountryClassification')
 if x in {'US','NON_US'}:return x,'NQ_EXPLICIT',[]
 if cins(h.get('mappedSecurityId')):return 'NON_US','CINS',[]
 if RECEIPT.search(str(h.get('description') or '')):return 'NON_US','ADR_GDR',[]
 u=[r for r in e.get(ik(h.get('mappedTicker'),h.get('mappedSecurityId')),[]) if r['evidenceDateFiled']<=signal];cs={r['classification'] for r in u}
 if len(cs)>1:raise RuntimeError(f'country conflict {ik(h.get("mappedTicker"),h.get("mappedSecurityId"))} {signal} {cs}')
 return (next(iter(cs)),'FROZEN_DATED_FILING',u) if cs else ('UNKNOWN','UNRESOLVED',[])
def unresolved(mapping,npx,base,struct):
 e=frozen(base,struct);iv=defaultdict(set)
 for r in npx.get('records',[]):
  if r.get('ticker') and (r.get('issuer') or r.get('normalizedIssuer')):iv[ik(r.get('ticker'),r.get('securityId'))].add(r.get('issuer') or r.get('normalizedIssuer'))
 rows=defaultdict(lambda:{'aggregateWeight':0.,'occurrenceCount':0,'issuerVariants':set()})
 for s in mapping['monthSnapshots']:
  for f in s['sourceFilings']:
   for h in f.get('holdings',[]):
    if h.get('legacyAssetSection')!='COMMON_EQUITY' or h.get('mappingStatus')!='MATCHED_UNIQUE' or not h.get('mappedTicker'):continue
    if static_country(h,s['asOf'],e)[0]!='UNKNOWN':continue
    k=ik(h.get('mappedTicker'),h.get('mappedSecurityId'));q=rows[(k[0],k[1],s['asOf'])];q['aggregateWeight']+=float(h.get('weight') or 0);q['occurrenceCount']+=1;q['issuerVariants'].update(iv.get(k,set()));q['issuerVariants'].add(str(h.get('description') or ''))
 out=[]
 for (t,sec,sd),r in sorted(rows.items()):out.append({'ticker':t,'securityId':sec,'signalDate':sd,'aggregateWeight':r['aggregateWeight'],'occurrenceCount':r['occurrenceCount'],'issuerVariants':sorted(x for x in r['issuerVariants'] if x)})
 return out
def resolve_one(row,flat,sm,master):
 forms=[]
 for issuer in row['issuerVariants']:
  for x in sm.cleaned_forms(str(issuer)):
   if x and x not in forms:forms.append(x)
 pos=[];attempts=[]
 for form in forms:
  q={'ticker':row['ticker'],'securityId':row['securityId'],'issuer':form,'aggregateWeight':row['aggregateWeight'],'asOfReportDate':row['signalDate']};ev=flat.resolve(q,master)
  attempts.append({k:ev.get(k) for k in ['classification','seedCik','seedSource','resolutionSource','stateCode','evidenceDateFiled']}|{'issuerForm':form})
  if ev.get('classification') in {'US','NON_US'}:
   ed=ev.get('evidenceDateFiled')
   if not ed or ed>row['signalDate']:raise RuntimeError(f'lookahead {row["ticker"]} {row["signalDate"]} {ed}')
   pos.append((ev['classification'],form,ev))
 cs={x[0] for x in pos}
 if len(cs)>1:raise RuntimeError(f'historical country conflict {row["ticker"]} {row["securityId"]} {row["signalDate"]} {cs}')
 if not pos:return {**row,'classification':'UNKNOWN','attempts':attempts}
 x=min(pos,key=lambda z:(z[2].get('evidenceDateFiled') or '9999',z[1]));return {**row,'classification':x[0],'countryIdentityFormUsed':x[1],'resolutionEvidence':x[2],'attempts':attempts}
def resolve_shard(a):
 m=json.loads(MAPPING.read_text());n=json.loads(NPX.read_text());b=json.loads(BASE.read_text());s=json.loads(STRUCT.read_text());u=unresolved(m,n,b,s);g=defaultdict(list)
 for r in u:g[(r['ticker'],r['securityId'])].append(r)
 ids=sorted(g);sel=[k for i,k in enumerate(ids) if i%a.shard_count==a.shard_index]
 flat=loadmod('flat',ROOT/'scripts/research-sec-submission-header-country-pilot-2006.py');sm=loadmod('sm',ROOT/'scripts/research-nq-npx-structural-mapping-2006.py');master,tr=flat.base.load_master([2005,2006]);out=[];calls=0
 for ii,k in enumerate(sel,1):
  carry=None
  for r in sorted(g[k],key=lambda x:x['signalDate']):
   if carry:
    q={**r,'classification':carry['classification'],'countryIdentityFormUsed':carry.get('countryIdentityFormUsed'),'resolutionEvidence':carry.get('resolutionEvidence'),'attempts':[],'carryForwardFromSignalDate':carry['signalDate']}
   else:
    q=resolve_one(r,flat,sm,master);calls+=1
    if q.get('classification') in {'US','NON_US'}:carry=q
   out.append(q);print('COUNTRY',json.dumps({'identityProgress':f'{ii}/{len(sel)}','ticker':q['ticker'],'signalDate':q['signalDate'],'classification':q['classification'],'carried':bool(q.get('carryForwardFromSignalDate'))}),flush=True)
 obj={'catalogSha256':CATALOG_SHA,'shardIndex':a.shard_index,'shardCount':a.shard_count,'fullUnresolvedIdentityDateCount':len(u),'selectedIdentityCount':len(sel),'selectedIdentityDateCount':sum(len(g[k]) for k in sel),'networkResolutionCount':calls,'resolvedUSCount':sum(r['classification']=='US' for r in out),'resolvedNonUSCount':sum(r['classification']=='NON_US' for r in out),'remainingUnknownCount':sum(r['classification']=='UNKNOWN' for r in out),'masterIndexTransports':tr,'rows':out}
 SHARDS.mkdir(parents=True,exist_ok=True);(SHARDS/f'nq-hybrid-country-pit-shard-{a.shard_index:02d}.json').write_text(json.dumps(obj,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in obj.items() if k not in {'rows','masterIndexTransports'}}),flush=True)
def shard_map():
 files=sorted(SHARDS.rglob('nq-hybrid-country-pit-shard-*.json'));r={};sc=set()
 if not files:raise RuntimeError('no shard files')
 for p in files:
  d=json.loads(p.read_text());sc.add(d['shardCount'])
  if d.get('catalogSha256')!=CATALOG_SHA:raise RuntimeError(f'hash mismatch {p}')
  for x in d['rows']:
   k=(x['ticker'],x['securityId'],x['signalDate'])
   if k in r:raise RuntimeError(f'duplicate {k}')
   r[k]=x
 if len(sc)!=1 or len(files)!=next(iter(sc)):raise RuntimeError(f'incomplete shards {len(files)} {sc}')
 return r,files
def classify(h,signal,e,r):
 c,reason,old=static_country(h,signal,e);new=None
 if c=='UNKNOWN' and h.get('mappingStatus')=='MATCHED_UNIQUE':
  k0=ik(h.get('mappedTicker'),h.get('mappedSecurityId'));new=r.get((k0[0],k0[1],signal))
  if new and new.get('classification') in {'US','NON_US'}:
   ed=(new.get('resolutionEvidence') or {}).get('evidenceDateFiled')
   if not ed or ed>signal:raise RuntimeError(f'merge lookahead {k0} {signal} {ed}')
   c=new['classification'];reason='PIT_SUBMISSION_HEADER'
 return c,reason,old,new
def filtered(f,mode):
 hs=[]
 for h in f.get('holdings',[]):
  if h.get('legacyAssetSection')!='COMMON_EQUITY' or h.get('mappingStatus')!='MATCHED_UNIQUE' or not h.get('mappedTicker') or float(h.get('weight') or 0)<=0:continue
  c=h.get('countryClassification','UNKNOWN')
  if c=='NON_US' or (c=='UNKNOWN' and mode=='primary') or noncorp(h.get('description')):continue
  hs.append(h)
 return sorted(hs,key=lambda x:float(x.get('weight') or 0),reverse=True)
def source_ok(f,mode):
 name=f.get('seriesName') or ''
 if STRUCTURED.search(name):return False,'STRUCTURED_OR_INCOME',[]
 if BROAD.search(name):return False,'BROAD_BENCHMARK',[]
 hs=filtered(f,mode)
 if not 10<=len(hs)<=120:return False,'HOLDING_COUNT',hs
 total=sum(float(h.get('weight') or 0) for h in hs);top=sum(float(h.get('weight') or 0) for h in hs[:10])
 if total<50:return False,'TOTAL_WEIGHT',hs
 if top<25:return False,'TOP10_WEIGHT',hs
 return True,'ELIGIBLE',hs
def universe(s,mode):
 rows={};audit=[]
 for f in s['sourceFilings']:
  ok,reason,hs=source_ok(f,mode);raw=[h for h in f.get('holdings',[]) if h.get('legacyAssetSection')=='COMMON_EQUITY'];mapped=[h for h in raw if h.get('mappingStatus')=='MATCHED_UNIQUE' and h.get('mappedTicker')];rw=sum(float(h.get('weight') or 0) for h in raw);mw=sum(float(h.get('weight') or 0) for h in mapped);audit.append({'seriesName':f.get('seriesName'),'canonicalIdentity':f.get('canonicalIdentity'),'filingDate':f.get('filingDate'),'eligible':ok,'eligibilityReason':reason,'filteredHoldingCount':len(hs),'filteredTotalWeight':sum(float(h.get('weight') or 0) for h in hs),'filteredTop10Weight':sum(float(h.get('weight') or 0) for h in hs[:10]),'rawCommonEquityCount':len(raw),'mappedCommonEquityCount':len(mapped),'mappedCommonEquityWeightRate':mw/rw if rw else None})
  if not ok:continue
  rf=math.exp(-max(0,(date.fromisoformat(s['asOf'])-date.fromisoformat(f['filingDate'])).days)/120);sid=f.get('canonicalIdentity') or f.get('seriesId') or f.get('legacyIdentity')
  for h in hs:
   sym=h['mappedTicker'].strip().upper();w=float(h.get('weight') or 0);q=rows.setdefault(sym,{'series':set(),'aggregateWeight':0.,'maxWeight':0.,'recencyWeight':0.});q['series'].add(sid);q['aggregateWeight']+=w;q['maxWeight']=max(q['maxWeight'],w);q['recencyWeight']+=w*rf
 out=[]
 for sym,q in rows.items():
  ec=len(q['series'])
  if ec<2 and q['maxWeight']<4:continue
  score=3*math.log1p(ec)+.5*math.log1p(q['aggregateWeight'])+.5*math.log1p(q['recencyWeight']);out.append({'symbol':sym,'etfCount':ec,'aggregateWeight':q['aggregateWeight'],'maxWeight':q['maxWeight'],'recencyWeight':q['recencyWeight'],'universeScore':score})
 out.sort(key=lambda x:(-x['universeScore'],-x['etfCount'],-x['aggregateWeight'],x['symbol']));return [{**x,'universeRank':i+1} for i,x in enumerate(out[:80])],audit
def spearman(a,b,common):
 n=len(common)
 if n<2:return None
 ra={x['symbol']:x['universeRank'] for x in a};rb={x['symbol']:x['universeRank'] for x in b};d2=sum((ra[x]-rb[x])**2 for x in common);return 1-6*d2/(n*(n*n-1))
def compare(p,u):
 k=min(len(p),len(u),80)
 if not k:return {'topK':0,'topKOverlap':None,'commonNameSpearman':None,'upperTop2IndividualRetention':None,'upperTop2BothRetained':None}
 ps={x['symbol'] for x in p[:k]};us={x['symbol'] for x in u[:k]};cm=sorted(ps&us);top=[x['symbol'] for x in u[:2]]
 return {'topK':k,'topKOverlap':len(cm)/k,'commonNameSpearman':spearman(p[:k],u[:k],cm),'upperTop2IndividualRetention':sum(x in ps for x in top)/len(top) if top else None,'upperTop2BothRetained':len(top)==2 and all(x in ps for x in top),'commonSymbols':cm}
def merge():
 m=json.loads(MAPPING.read_text());n=json.loads(NPX.read_text());b=json.loads(BASE.read_text());s0=json.loads(STRUCT.read_text());e=frozen(b,s0);r,files=shard_map();exp=unresolved(m,n,b,s0);keys={(x['ticker'],x['securityId'],x['signalDate']) for x in exp}
 if set(r)!=keys:raise RuntimeError(f'shard coverage mismatch missing={len(keys-set(r))} extra={len(set(r)-keys)}')
 snaps=[];reasons=Counter()
 for s in m['monthSnapshots']:
  counts=Counter();weights=defaultdict(float);fs=[];ncorp=0;ncorpw=0.
  for f in s['sourceFilings']:
   hs=[]
   for h0 in f.get('holdings',[]):
    h=dict(h0)
    if h.get('legacyAssetSection')=='COMMON_EQUITY' and h.get('mappingStatus')=='MATCHED_UNIQUE':c,reason,old,new=classify(h,s['asOf'],e,r)
    else:c,reason,old,new='UNKNOWN','OUTSIDE_MAPPED_COMMON_EQUITY',[],None
    h['countryClassification']=c;h['countryReason']=reason
    if old:h['countryEvidence']=old
    if new:h['countryResolutionEvidence']=new
    sig=noncorp(h.get('description')) if h.get('legacyAssetSection')=='COMMON_EQUITY' and c=='US' else [];h['corpBridgeEligible']=bool(h.get('legacyAssetSection')=='COMMON_EQUITY' and c=='US' and not sig);h['corpBridgeReason']='EC_US_NO_POSITIVE_NONCORP_SIGNAL' if h['corpBridgeEligible'] else ('POSITIVE_NONCORP_NAME_SIGNAL' if sig else 'NOT_US_COMMON_EQUITY')
    if sig:h['nonCorpSignals']=sig;ncorp+=1;ncorpw+=float(h.get('weight') or 0)
    if h.get('legacyAssetSection')=='COMMON_EQUITY' and h.get('mappingStatus')=='MATCHED_UNIQUE':counts[c]+=1;weights[c]+=float(h.get('weight') or 0);reasons[reason]+=1
    hs.append(h)
   fs.append({**{k:v for k,v in f.items() if k!='holdings'},'holdings':hs})
  snaps.append({**{k:v for k,v in s.items() if k!='sourceFilings'},'mappedCommonEquityCountryCounts':dict(counts),'mappedCommonEquityCountryWeights':dict(weights),'corpPositiveNonCorpNameCount':ncorp,'corpPositiveNonCorpNameWeight':ncorpw,'sourceFilings':fs});print('MONTH_COUNTRY',json.dumps({'signalMonth':s['signalMonth'],'counts':dict(counts),'weights':dict(weights),'corpPositiveNonCorpNameCount':ncorp}),flush=True)
 country={'purpose':'Hybrid H1 2006 mapped COMMON_EQUITY PIT country. Filing evidence requires evidenceDateFiled<=signalDate; UNKNOWN is never imputed US. CORP is an explicit structural bridge after US: positive registered/private-fund, sovereign/government or municipal name signals are excluded.','catalogSha256':CATALOG_SHA,'productionEligibilityOrder':['COMMON_EQUITY','US','CORP','SOURCE_ELIGIBILITY'],'countryEvidenceRule':'same-filing explicit -> CINS/ADR/GDR NON_US -> historical SEC filing evidenceDateFiled<=signalDate -> UNKNOWN','corpBridgeRule':'EC+confirmed US minus positive non-CORP name signals; transition EC+US was 226/226 CORP and full H1 2006 positive-name exceptions are audited','frozenDatedEvidenceIdentityCount':len(e),'resolvedShardFileCount':len(files),'unresolvedIdentityDateInputCount':len(exp),'reasonCounts':dict(reasons),'monthSnapshots':snaps};COUNTRY_OUT.write_text(json.dumps(country,indent=2)+'\n')
 months=[]
 for s in snaps:
  p,pa=universe(s,'primary');u,ua=universe(s,'upper');c=compare(p,u);months.append({'signalMonth':s['signalMonth'],'asOf':s['asOf'],'sourceSeriesCount':len(s['sourceFilings']),'primaryEligibleSourceSeriesCount':sum(x['eligible'] for x in pa),'upperBoundEligibleSourceSeriesCount':sum(x['eligible'] for x in ua),'primaryUniverseSize':len(p),'upperBoundUniverseSize':len(u),**c,'primarySymbols':p,'upperBoundSymbols':u,'primarySourceEligibilityAudit':pa,'upperBoundSourceEligibilityAudit':ua});print('MONTH_GATE_B',json.dumps({'signalMonth':s['signalMonth'],'primaryEligibleSources':sum(x['eligible'] for x in pa),'upperEligibleSources':sum(x['eligible'] for x in ua),'primaryUniverseSize':len(p),'upperUniverseSize':len(u),**{k:c.get(k) for k in ['topK','topKOverlap','commonNameSpearman','upperTop2IndividualRetention','upperTop2BothRetained']}}),flush=True)
 ovs=[x['topKOverlap'] for x in months if x['topKOverlap'] is not None];spr=[x['commonNameSpearman'] for x in months if x['commonNameSpearman'] is not None];t2=[x['upperTop2IndividualRetention'] for x in months if x['upperTop2IndividualRetention'] is not None];both=[x['upperTop2BothRetained'] for x in months if x['upperTop2IndividualRetention'] is not None];summary={'medianTopKOverlap':statistics.median(ovs) if ovs else None,'minimumMonthlyTopKOverlap':min(ovs) if ovs else None,'medianCommonNameSpearman':statistics.median(spr) if spr else None,'upperBoundTop2IndividualRetention':statistics.mean(t2) if t2 else None,'upperBoundBothTop2RetainedMonthRate':statistics.mean(both) if both else None,'evaluatedMonthCount':len(months),'monthsWithRankCorrelation':len(spr)};thr={'medianTopKOverlap':.80,'minimumMonthlyTopKOverlap':.70,'medianCommonNameSpearman':.75,'top2IndividualRetention':.80,'bothTop2RetainedMonthRate':.70};passed=bool(len(months)==len(ovs)==len(spr)==6 and summary['medianTopKOverlap']>=.80 and summary['minimumMonthlyTopKOverlap']>=.70 and summary['medianCommonNameSpearman']>=.75 and summary['upperBoundTop2IndividualRetention']>=.80 and summary['upperBoundBothTop2RetainedMonthRate']>=.70)
 gate={'purpose':'Gate-B H1 2006 structural diagnostic after authoritative hybrid source selection and Production-order eligibility. Primary excludes UNKNOWN; upper bound treats only already-mapped UNKNOWN country as US/CORP eligible. Upper bound is diagnostic only and never tunes rules.','catalogSha256':CATALOG_SHA,'productionEligibilityOrder':['COMMON_EQUITY','US','CORP','SOURCE_ELIGIBILITY'],'productionSourceEligibility':{'holdingCount':[10,120],'minimumTotalWeight':50,'minimumTop10Weight':25,'nameExclusions':'same as src/lib/universe/sec-nport.ts'},'productionBreadthRule':'etfCount>=2 OR maxWeight>=4; score=3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight); Top80','gateAEquivalentPracticalThresholds':thr,'transitionEvidenceAlreadyAccepted':{'2020_01TopKOverlap':8/9,'2020_01CommonNameSpearman':.842,'2020_01ProductionTop2Retained':'2/2','transitionECUSCorp':'226/226'},'countryUpperBoundSensitivitySummary':summary,'countryUpperBoundSensitivityPass':passed,'note':'This sensitivity does not infer symbols for unmapped holdings and therefore does not by itself erase residual mapping uncertainty.','monthSnapshots':months};GATE_OUT.write_text(json.dumps(gate,indent=2)+'\n');print('GATE_B_SUMMARY',json.dumps({**summary,'countryUpperBoundSensitivityPass':passed}),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['resolve-shard','merge'],required=True);p.add_argument('--shard-index',type=int,default=int(os.getenv('SHARD_INDEX','0')));p.add_argument('--shard-count',type=int,default=int(os.getenv('SHARD_COUNT','1')));a=p.parse_args()
 if a.mode=='resolve-shard':
  if a.shard_count<1 or not 0<=a.shard_index<a.shard_count:raise ValueError('invalid shard configuration')
  resolve_shard(a)
 else:merge()
if __name__=='__main__':main()
