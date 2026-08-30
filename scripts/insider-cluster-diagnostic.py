import json,math,subprocess,sys
from pathlib import Path
from datetime import date,timedelta
try: import duckdb
except Exception:
 subprocess.check_call([sys.executable,'-m','pip','install','duckdb==1.4.0','-q']); import duckdb
URL='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/insider_transactions/insider_transactions-00000-of-00001.parquet?download=true'

def mean(a): return sum(a)/len(a) if a else None
def med(a):
 if not a:return None
 x=sorted(a); n=len(x); return x[n//2] if n%2 else (x[n//2-1]+x[n//2])/2
def ranks(a):
 o=sorted(range(len(a)),key=lambda i:a[i]); r=[0.0]*len(a); i=0
 while i<len(o):
  j=i
  while j+1<len(o) and a[o[j+1]]==a[o[i]]: j+=1
  rr=(i+j)/2+1
  for k in range(i,j+1): r[o[k]]=rr
  i=j+1
 return r
def spearman(a,b):
 if len(a)<20:return None
 x,y=ranks(a),ranks(b); mx,my=mean(x),mean(y); n=dx=dy=0.0
 for p,q in zip(x,y):
  u,v=p-mx,q-my;n+=u*v;dx+=u*u;dy+=v*v
 return n/math.sqrt(dx*dy) if dx and dy else None

def future(arr,signal,n):
 ds=[p['date'] for p in arr]
 try:i=ds.index(signal)
 except ValueError:return None
 if i+1>=len(arr) or i+n>=len(arr):return None
 e=arr[i+1].get('open') or arr[i+1].get('close'); z=arr[i+n].get('close')
 return z/e-1 if e and z and e>0 else None

u=json.loads(Path('data/universe-history.json').read_text())['history']; u=sorted([x for x in u if '2020-01-01'<=x['asOf']<='2026-08-25'],key=lambda x:x['asOf'])
market=json.loads(Path('public/data/market-data.json').read_text())['histories']
syms=sorted({m['symbol'] for x in u for m in x['symbols']}); aliases={'GOOG':'GOOGL'}
# Role flags in the mirror are not populated for P transactions, so use all reported Form 4 open-market purchases.
# PIT is preserved with filed_at < signal date; same-day filings remain excluded.
con=duckdb.connect();con.execute('INSTALL httpfs');con.execute('LOAD httpfs');con.execute('create temp table wanted(ticker varchar)');con.executemany('insert into wanted values (?)',[(aliases.get(s,s),) for s in syms])
q=f"""select upper(t.issuer_ticker) ticker,t.owner_cik,t.filed_at,t.accession,t.value_usd
from read_parquet('{URL}') t join wanted w on upper(t.issuer_ticker)=w.ticker
where t.form_type='4' and t.transaction_code='P' and t.acquired_disposed='A'
 and coalesce(t.value_usd,0)>0
 and cast(t.filed_at as date)>=date '2019-12-01' and cast(t.filed_at as date)<=date '2026-08-25'"""
rows=con.execute(q).fetchall(); by={}
for ticker,owner,filed,acc,val in rows:
 d=str(filed)[:10]; by.setdefault(ticker,[]).append((d,int(owner) if owner is not None else -1,acc,float(val or 0)))
for k in by:by[k].sort()
obs=[]
for x in u:
 d=x['asOf']; sd=date.fromisoformat(d); lo=(sd-timedelta(days=30)).isoformat()
 for m in x['symbols']:
  s=m['symbol']; arr=market.get(s)
  if not arr:continue
  raw=by.get(aliases.get(s,s),[])
  w=[r for r in raw if lo<=r[0]<d]
  buyers=len(set(r[1] for r in w if r[1]!=-1)); val=sum(r[3] for r in w)
  r21=future(arr,d,21);r63=future(arr,d,63)
  if r21 is None or r63 is None:continue
  obs.append({'date':d,'symbol':s,'buyers30':buyers,'buyValue30':val,'cluster':buyers>=2,'r21':r21,'r63':r63})

def summ(start,end):
 x=[r for r in obs if start<=r['date']<=end]; cl=[r for r in x if r['cluster']]; z=[r for r in x if r['buyers30']==0]
 return {'observations':len(x),'clusterObs':len(cl),'clusterShare':len(cl)/len(x) if x else None,'icBuyers21':spearman([r['buyers30'] for r in x],[r['r21'] for r in x]),'icBuyers63':spearman([r['buyers30'] for r in x],[r['r63'] for r in x]),'clusterMeanR21':mean([r['r21'] for r in cl]),'zeroMeanR21':mean([r['r21'] for r in z]),'clusterMinusZeroR21':(mean([r['r21'] for r in cl])-mean([r['r21'] for r in z])) if cl and z else None,'clusterMeanR63':mean([r['r63'] for r in cl]),'zeroMeanR63':mean([r['r63'] for r in z]),'clusterMinusZeroR63':(mean([r['r63'] for r in cl])-mean([r['r63'] for r in z])) if cl and z else None,'clusterMedianR21':med([r['r21'] for r in cl]),'zeroMedianR21':med([r['r21'] for r in z]),'clusterMedianR63':med([r['r63'] for r in cl]),'zeroMedianR63':med([r['r63'] for r in z])}
out={'generatedAt':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'validity':{'researchOnly':True,'trueOOS':False,'pit':True,'freeDataOnly':True,'diagnosticOnly':True,'source':'SEC Form 4 bulk data via DataForge mirror','rawOnly':True,'rule':'Form4 code P + acquired A + value>0; unique reporting owners filed in prior 30 calendar days; same-day filings excluded; future starts next open','roleFlagIssue':'mirror is_director/is_officer fields are unpopulated for P rows; role filter intentionally removed','parameterSearch':False},'coverage':{'dynamicSymbols':len(syms),'rawPurchaseRows':len(rows),'tickersWithPurchases':len(by),'observations':len(obs)},'diagnostic':{'early2020_2023':summ('2020-01-01','2023-12-31'),'late2024_2026':summ('2024-01-01','2026-08-25')},'rows':obs}
p=Path('data/research/insider-cluster-diagnostic');p.mkdir(parents=True,exist_ok=True);(p/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
