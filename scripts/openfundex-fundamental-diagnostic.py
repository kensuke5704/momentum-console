import json, math, subprocess, sys, urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

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
    order=sorted(range(len(a)),key=lambda i:a[i]); r=[0.0]*len(a); i=0
    while i<len(order):
        j=i
        while j+1<len(order) and a[order[j+1]]==a[order[i]]: j+=1
        rr=(i+j)/2+1
        for k in range(i,j+1): r[order[k]]=rr
        i=j+1
    return r
def spearman(a,b):
    if len(a)<4 or len(a)!=len(b): return None
    x,y=ranks(a),ranks(b); mx,my=mean(x),mean(y); n=dx=dy=0.0
    for p,q in zip(x,y):
        u,v=p-mx,q-my; n+=u*v; dx+=u*u; dy+=v*v
    return n/math.sqrt(dx*dy) if dx>0 and dy>0 else None

def parse_date(s): return date.fromisoformat(str(s)[:10])
def days(a,b): return (a-b).days

top=json.loads(Path('data/research/production-top10-monthly/result.json').read_text())
wanted=set(top['symbols']); aliases={'GOOGL':'GOOG'}
query_tickers=sorted(wanted|set(aliases.values()))
con=duckdb.connect(); paths=','.join("'"+str(D/f)+"'" for f in FILES)
con.execute('create temp table wanted(ticker varchar)'); con.executemany('insert into wanted values (?)',[(x,) for x in query_tickers])
q=f"""
select cik,upper(ticker) ticker,adsh,filing_date,period_end_date,fiscal_quarter,revenue,operating_income,qa_pass,source_file
from read_parquet([{paths}], union_by_name=true) d
join wanted w on upper(d.ticker)=w.ticker
where filing_date between date '2018-01-01' and date '2026-08-25'
  and qa_pass is true and revenue is not null
order by ticker, filing_date, period_end_date
"""
cols=[x[0] for x in con.execute(q).description]; raw=[dict(zip(cols,r)) for r in con.fetchall()]
# Normalize to point-in-time quarterly observations. Q1-Q3 are direct. Q4 is implied from FY less the three preceding direct quarters.
by=defaultdict(list)
for r in raw:
    r['filing_date']=parse_date(r['filing_date']); r['period_end_date']=parse_date(r['period_end_date']); by[r['ticker']].append(r)
facts=defaultdict(list)
for ticker,rows in by.items():
    rows=sorted(rows,key=lambda r:(r['filing_date'],r['period_end_date'],r['adsh']))
    direct=[r for r in rows if r['fiscal_quarter'] in ('Q1','Q2','Q3')]
    for r in direct:
        facts[ticker].append({'filed':r['filing_date'],'period':r['period_end_date'],'quarter':r['fiscal_quarter'],'rev':float(r['revenue']),'op':None if r['operating_income'] is None else float(r['operating_income']),'adsh':r['adsh'],'source':r['source_file'],'derivedQ4':False})
    for fy in [r for r in rows if r['fiscal_quarter']=='FY']:
        prior=[r for r in direct if r['filing_date']<=fy['filing_date'] and r['period_end_date']<fy['period_end_date'] and 30<=days(fy['period_end_date'],r['period_end_date'])<=330]
        # one latest-filed observation per period; then take the nearest three quarter ends
        per={}
        for r in prior:
            if r['period_end_date'] not in per or r['filing_date']>per[r['period_end_date']]['filing_date']: per[r['period_end_date']]=r
        xs=sorted(per.values(),key=lambda r:r['period_end_date'],reverse=True)[:3]
        if len(xs)==3 and all(x['revenue'] is not None for x in xs):
            rev=float(fy['revenue'])-sum(float(x['revenue']) for x in xs)
            op=None
            if fy['operating_income'] is not None and all(x['operating_income'] is not None for x in xs): op=float(fy['operating_income'])-sum(float(x['operating_income']) for x in xs)
            if rev>0:
                facts[ticker].append({'filed':fy['filing_date'],'period':fy['period_end_date'],'quarter':'Q4','rev':rev,'op':op,'adsh':fy['adsh'],'source':fy['source_file'],'derivedQ4':True})
for k in facts: facts[k].sort(key=lambda r:(r['filed'],r['period'],r['adsh']))

def available(symbol,signal):
    t=aliases.get(symbol,symbol); sd=parse_date(signal); rows=[r for r in facts.get(t,[]) if r['filed']<=sd]
    per={}
    for r in rows:
        if r['period'] not in per or r['filed']>per[r['period']]['filed']: per[r['period']]=r
    return sorted(per.values(),key=lambda r:r['period'])
def year_match(rows,idx):
    cur=rows[idx]; candidates=[(abs(days(cur['period'],r['period'])-365),j,r) for j,r in enumerate(rows[:idx]) if 320<=days(cur['period'],r['period'])<=410]
    return min(candidates,key=lambda x:x[0])[1] if candidates else None
def metric(symbol,signal):
    rows=available(symbol,signal)
    if len(rows)<6: return None
    i=len(rows)-1; y=year_match(rows,i)
    margin=None
    if y is not None and rows[i]['op'] is not None and rows[y]['op'] is not None and rows[i]['rev'] and rows[y]['rev']:
        margin=rows[i]['op']/rows[i]['rev']-rows[y]['op']/rows[y]['rev']
    sales=None
    if i>=1:
        y0=y; y1=year_match(rows,i-1)
        if y0 is not None and y1 is not None and rows[y0]['rev'] and rows[y1]['rev']:
            g0=rows[i]['rev']/rows[y0]['rev']-1; g1=rows[i-1]['rev']/rows[y1]['rev']-1; sales=g0-g1
    return {'salesAccel':sales,'marginDelta':margin,'latestPeriod':rows[i]['period'].isoformat(),'latestFiled':rows[i]['filed'].isoformat()}

market=json.loads(Path('public/data/market-data.json').read_text())['histories']
price_maps={s:{p['date']:p for p in arr} for s,arr in market.items()}; dates={s:[p['date'] for p in arr] for s,arr in market.items()}
def future(symbol,signal,n):
    arr=market.get(symbol); ds=dates.get(symbol)
    if not arr or signal not in ds: return None
    i=ds.index(signal)
    if i+1>=len(arr): return None
    j=min(i+n,len(arr)-1); start=arr[i+1].get('open') or arr[i+1].get('close'); end=arr[j].get('open') or arr[j].get('close')
    return end/start-1 if start and end and start>0 and end>0 else None
monthly=[]; detail=[]
for m in top['monthly']:
    d=m['date']; vals={'salesAccel':[],'marginDelta':[]}
    for c in m['top10']:
        sym=c['symbol']; met=metric(sym,d); r1=future(sym,d,21); r3=future(sym,d,63)
        if met: detail.append({'date':d,'symbol':sym,**met,'r1':r1,'r3':r3})
        for f in vals:
            v=met.get(f) if met else None
            if v is not None and math.isfinite(v) and r1 is not None and r3 is not None: vals[f].append((v,r1,r3))
    row={'date':d,'top10':len(m['top10'])}
    for f,x in vals.items():
        row[f]={'n':len(x),'ic1':spearman([z[0] for z in x],[z[1] for z in x]),'ic3':spearman([z[0] for z in x],[z[2] for z in x])}
    monthly.append(row)
def summary(f,start,end):
    x=[r[f] for r in monthly if start<=r['date']<=end and r[f]['ic1'] is not None and r[f]['ic3'] is not None]
    return {'months':len(x),'meanIC1':mean([r['ic1'] for r in x]),'meanIC3':mean([r['ic3'] for r in x]),'positiveIC1Share':sum(r['ic1']>0 for r in x)/len(x) if x else None,'positiveIC3Share':sum(r['ic3']>0 for r in x)/len(x) if x else None,'meanCoverage':mean([r['n']/10 for r in x]) if x else None}
out={'generatedAt':__import__('datetime').datetime.utcnow().isoformat()+'Z','validity':{'researchOnly':True,'trueOOS':False,'freeDataOnly':True,'pit':True,'diagnosticOnly':True,'source':'OpenFundex CC-BY-4.0 mirror of SEC FSDS','rawFieldsOnly':['filing_date','period_end_date','revenue','operating_income','adsh'],'forwardTargetColumnsUsed':False,'rule':'filed <= signal close; Production 0/20/80 Momentum Top10; Q4 derived mechanically as FY less preceding Q1-Q3; no rerank/backtest unless factor direction is stable.'},'coverage':{'productionTop10Union':top['count'],'tickerFacts':len(facts),'missing':sorted([s for s in wanted if aliases.get(s,s) not in facts])},'diagnostic':{f:{'early2020_2023':summary(f,'2020-01-01','2023-12-31'),'late2024_2026':summary(f,'2024-01-01','2026-08-25')} for f in ['salesAccel','marginDelta']},'monthly':monthly}
outdir=Path('data/research/openfundex-fundamental-diagnostic'); outdir.mkdir(parents=True,exist_ok=True); (outdir/'result.json').write_text(json.dumps(out,indent=2,default=str));
# Freeze only raw PIT-relevant facts for reproducibility if the diagnostic later passes.
freeze={'provenance':{'dataset':'ttchopper/openfundex','files':FILES,'source':'SEC FSDS via OpenFundex','extractedFields':['ticker','filed','period','quarter','revenue','operatingIncome','adsh','source_file','derivedQ4']},'facts':{k:[{'filed':r['filed'].isoformat(),'period':r['period'].isoformat(),'quarter':r['quarter'],'revenue':r['rev'],'operatingIncome':r['op'],'adsh':r['adsh'],'source_file':r['source'],'derivedQ4':r['derivedQ4']} for r in v] for k,v in facts.items()}}
(outdir/'facts.json').write_text(json.dumps(freeze,separators=(',',':')))
print(json.dumps({k:v for k,v in out.items() if k!='monthly'},indent=2))
