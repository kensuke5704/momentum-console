import json, math, subprocess, sys, urllib.request
from bisect import bisect_left, bisect_right
from pathlib import Path
from collections import defaultdict
from datetime import date

BASE='https://huggingface.co/datasets/ttchopper/openfundex/resolve/main/'
FILES=['validation.parquet','test.parquet','recent.parquet']
D=Path('/tmp/openfundex'); D.mkdir(exist_ok=True)
for f in FILES:
    p=D/f
    if not p.exists(): urllib.request.urlretrieve(BASE+f+'?download=true',p)
try: import duckdb
except Exception:
    subprocess.check_call([sys.executable,'-m','pip','install','duckdb==1.4.0','-q']); import duckdb

def mean(a): return sum(a)/len(a) if a else None
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
    x,y=ranks(a),ranks(b); mx,my=mean(x),mean(y); num=dx=dy=0.0
    for p,q in zip(x,y):
        u,v=p-mx,q-my; num+=u*v; dx+=u*u; dy+=v*v
    return num/math.sqrt(dx*dy) if dx and dy else None
def qmean(rows,key,high=True):
    xs=[r for r in rows if r.get(key) is not None]
    if len(xs)<20:return None
    xs=sorted(xs,key=lambda r:r['reaction']); n=max(1,len(xs)//4); use=xs[-n:] if high else xs[:n]
    return mean([r[key] for r in use])

market=json.loads(Path('public/data/market-data.json').read_text())['histories']
uh=json.loads(Path('data/universe-history.json').read_text())['history']
uh=sorted(uh,key=lambda x:x['asOf']); udates=[x['asOf'] for x in uh]
all_syms=sorted({m['symbol'] for x in uh for m in x['symbols']})
alias={'GOOGL':'GOOG'}; query=sorted(set(alias.get(s,s) for s in all_syms))
con=duckdb.connect(); con.execute('create temp table wanted(ticker varchar)'); con.executemany('insert into wanted values (?)',[(x,) for x in query])
paths=','.join("'"+str(D/f)+"'" for f in FILES)
q=f"""select d.cik,upper(d.ticker) ticker,d.adsh,d.filing_date,d.period_end_date,d.fiscal_quarter,d.qa_pass
from read_parquet([{paths}],union_by_name=true) d join wanted w on upper(d.ticker)=w.ticker
where d.filing_date between date '2019-01-01' and date '2026-08-25' and d.qa_pass is true
  and d.fiscal_quarter in ('Q1','Q2','Q3','FY')
order by d.ticker,d.filing_date,d.adsh"""
cols=[x[0] for x in con.execute(q).description]; raw=[dict(zip(cols,r)) for r in con.fetchall()]
# One filing event per ticker/date/accession; OpenFundex can repeat rows across source partitions.
seen=set(); filings=[]
for r in raw:
    k=(r['ticker'],str(r['filing_date'])[:10],r['adsh'])
    if k in seen: continue
    seen.add(k); filings.append({'ticker':r['ticker'],'filed':str(r['filing_date'])[:10],'adsh':r['adsh'],'fq':r['fiscal_quarter']})
# reverse alias permits GOOG facts for either class, but prefer exact market ticker if present.
fact_to_market=defaultdict(list)
for s in all_syms: fact_to_market[alias.get(s,s)].append(s)

def active(sym,d):
    i=bisect_right(udates,d)-1
    if i<0:return False
    return any(m['symbol']==sym for m in uh[i]['symbols'])
def event_row(sym,filed):
    arr=market.get(sym)
    if not arr:return None
    ds=[p['date'] for p in arr]
    # Conservative: first full trading session strictly AFTER filing date. We only observe its close.
    i=bisect_right(ds,filed)
    if i<1 or i+63>=len(arr): return None
    p=arr[i]; op=p.get('open'); cl=p.get('close')
    if not op or not cl or op<=0:return None
    signal=ds[i]
    if not active(sym,signal):return None
    reaction=cl/op-1
    entry=arr[i+1].get('open') or arr[i+1].get('close')
    if not entry or entry<=0:return None
    r21=(arr[i+21].get('close')/entry-1) if arr[i+21].get('close') else None
    r63=(arr[i+63].get('close')/entry-1) if arr[i+63].get('close') else None
    return {'symbol':sym,'filed':filed,'signal':signal,'reaction':reaction,'r21':r21,'r63':r63}
rows=[]
for f in filings:
    cands=fact_to_market.get(f['ticker'],[])
    for sym in cands:
        x=event_row(sym,f['filed'])
        if x: x.update({'adsh':f['adsh'],'fq':f['fq']}); rows.append(x); break

def summ(start,end):
    x=[r for r in rows if start<=r['signal']<=end and r['r21'] is not None and r['r63'] is not None]
    return {'events':len(x),'ic21':spearman([r['reaction'] for r in x],[r['r21'] for r in x]),'ic63':spearman([r['reaction'] for r in x],[r['r63'] for r in x]),'topQuartileR21':qmean(x,'r21',True),'bottomQuartileR21':qmean(x,'r21',False),'topQuartileR63':qmean(x,'r63',True),'bottomQuartileR63':qmean(x,'r63',False),'positiveReactionShare':sum(r['reaction']>0 for r in x)/len(x) if x else None}
out={'generatedAt':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'validity':{'researchOnly':True,'trueOOS':False,'freeDataOnly':True,'pit':True,'diagnosticOnly':True,'source':'OpenFundex mirror of SEC FSDS + existing adjusted OHLC','informationLag':'filing date is ignored; reaction uses first full US session strictly after filing date; score observable at that close; future starts next open','noParameterSearch':True},'coverage':{'dynamicUniverseSymbols':len(all_syms),'factTickers':len(set(f['ticker'] for f in filings)),'events':len(rows)},'diagnostic':{'early2020_2023':summ('2020-01-01','2023-12-31'),'late2024_2026':summ('2024-01-01','2026-08-25')},'rows':rows}
outdir=Path('data/research/sec-filing-drift-diagnostic'); outdir.mkdir(parents=True,exist_ok=True); (outdir/'result.json').write_text(json.dumps(out,indent=2)); print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
