#!/usr/bin/env python3
from __future__ import annotations
import html,io,json,os,re,time,urllib.request,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/sec-marketwide-nq-inventory-h1-2006.json'
SHARD_INDEX=int(os.environ.get('SHARD_INDEX','0'));SHARD_COUNT=int(os.environ.get('SHARD_COUNT','1'))
OUT=ROOT/f'data/research/sec-etf-registrant-operational-prefilter-h1-2006-shard-{SHARD_INDEX:02d}.json'
CUTOFF='2006-06-30'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,application/zip,*/*','Accept-Encoding':'identity'}
CORE_FORMS={'485BPOS','485APOS','485BXT','N-1A','N-1A/A'};SUPP={'497'};ALL=CORE_FORMS|SUPP
CRE=[re.compile(r'(?is)(?:offers?|issues?|sells?)\s+(?:and\s+\w+\s+)*shares?.{0,900}?creation\s+units?'),re.compile(r'(?is)shares?.{0,900}?(?:redeemable|redeemed|redemptions?).{0,500}?creation\s+units?'),re.compile(r'(?is)creation\s+units?.{0,500}?(?:issued|redeemed|purchase|redemption).{0,500}?shares?')]
EX=[re.compile(r'(?is)shares?.{0,700}?(?:listed|traded).{0,300}?(?:national\s+securities\s+exchange|exchange|amex|nyse|nasdaq)'),re.compile(r'(?is)(?:listed|traded).{0,300}?(?:national\s+securities\s+exchange|exchange|amex|nyse|nasdaq).{0,700}?shares?')]
SPACE=re.compile(r'\s+')
def fb(url,limit,timeout=18):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(limit),getattr(r,'status',None)
def ft(url,limit=2_000_000,timeout=18):
 errs=[]
 for u in (url,'https://r.jina.ai/'+url):
  try:b,s=fb(u,limit,timeout);return b.decode('latin-1','replace'),u,s,errs
  except Exception as e:errs.append({'transport':u,'error':type(e).__name__})
 raise RuntimeError(json.dumps(errs))
def master(y,q):
 base=f'https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}';zu=base+'/master.zip'
 try:
  b,_=fb(zu,25_000_000,45)
  with zipfile.ZipFile(io.BytesIO(b)) as z:n=next(x for x in z.namelist() if x.lower().endswith('master.idx'));return z.read(n).decode('latin-1','replace'),zu
 except Exception:
  t,u,_,_=ft(base+'/master.idx',25_000_000,50);return t,u
def load(ciks):
 by=defaultdict(list);trs={}
 for y,qs in ((2005,range(1,5)),(2006,range(1,3))):
  for q in qs:
   t,tr=master(y,q);trs[f'{y}Q{q}']=tr
   for ln in t.splitlines():
    p=ln.split('|')
    if len(p)<5 or not p[0].strip().isdigit():continue
    cik,co,form,date,fn=[x.strip() for x in p[:5]];cik=cik.zfill(10);form=form.upper()
    if cik in ciks and form in ALL and date<=CUTOFF:by[cik].append({'cik':cik,'company':co,'form':form,'dateFiled':date,'filename':fn})
 return by,trs
def su(fn):return 'https://www.sec.gov/Archives/'+fn.lstrip('/')
def fm(ps,t):
 for p in ps:
  m=p.search(t)
  if m:return m
 return None
def sn(t,m,r=150):
 if not m:return None
 return SPACE.sub(' ',html.unescape(t[max(0,m.start()-r):min(len(t),m.end()+r)])).strip()
def choose(rows):
 core=sorted((x for x in rows if x['form'] in CORE_FORMS),key=lambda x:(x['dateFiled'],x['form'],x['filename']),reverse=True)
 supp=sorted((x for x in rows if x['form'] in SUPP),key=lambda x:(x['dateFiled'],x['form'],x['filename']),reverse=True)
 return ([core[0]] if core else [])+([supp[0]] if supp else [])
def main():
 d=json.loads(SRC.read_text());bynq=defaultdict(list)
 for x in d['rows']:bynq[x['cik']].append(x)
 ciks=sorted(bynq);sel=[c for i,c in enumerate(ciks) if i%SHARD_COUNT==SHARD_INDEX];bp,trs=load(set(sel));results=[]
 for cik in sel:
  nqs=sorted(bynq[cik],key=lambda x:(x['dateFiled'],x['accession']));pool=bp.get(cik,[]);cand=choose(pool);rec={'cik':cik,'companyNames':sorted({x['company'] for x in nqs}),'nqFilingCount':len(nqs),'nqFirstDate':nqs[0]['dateFiled'],'nqLastDate':nqs[-1]['dateFiled'],'prospectusCandidatePoolCount':len(pool),'checkedCandidateCount':len(cand),'candidateRegistrant':False,'attempts':[]}
  for f in cand:
   a={k:f[k] for k in ('form','dateFiled','filename')};url=su(f['filename'])
   try:
    t,tr,status,prior=ft(url);c=fm(CRE,t);e=fm(EX,t);a.update({'submissionUrl':url,'transport':tr,'httpStatus':status,'priorTransportErrors':prior,'creationOperationalEvidence':bool(c),'exchangeTradingEvidence':bool(e),'jointOperationalEvidence':bool(c and e),'creationSnippet':sn(t,c),'exchangeSnippet':sn(t,e)})
    if c and e:rec['candidateRegistrant']=True;rec['positiveEvidence']={'form':f['form'],'dateFiled':f['dateFiled'],'filename':f['filename'],'submissionUrl':url,'creationSnippet':a['creationSnippet'],'exchangeSnippet':a['exchangeSnippet']}
   except Exception as e:a.update({'submissionUrl':url,'error':type(e).__name__})
   rec['attempts'].append(a)
   if rec['candidateRegistrant']:break
   time.sleep(.02)
  results.append(rec);print('REG',json.dumps({'cik':cik,'candidate':rec['candidateRegistrant'],'nq':len(nqs),'pool':len(pool)}),flush=True)
 pos=[x for x in results if x['candidateRegistrant']]
 out={'purpose':'Candidate-only registrant prefilter for every CIK in the fixed official SEC H1 2006 N-Q/N-Q-A inventory. Positive requires joint Creation Unit and exchange-listing/trading operational evidence in the deterministic newest core prospectus or newest 497 filed by 2006-06-30. This is not final series-level ETF classification; negatives are not final exclusions until recall is audited. No known source list, holdings, ranks, returns, or strategy outcomes are used.','inventoryArtifactId':9946255797,'cutoff':CUTOFF,'shardIndex':SHARD_INDEX,'shardCount':SHARD_COUNT,'fullRegistrantCount':len(ciks),'selectedRegistrantCount':len(sel),'registrantsWithProspectusCandidates':sum(bool(bp.get(c)) for c in sel),'positiveCandidateRegistrantCount':len(pos),'positiveCiks':[x['cik'] for x in pos],'masterTransports':trs,'results':results}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('results','masterTransports')}),flush=True)
if __name__=='__main__':main()
