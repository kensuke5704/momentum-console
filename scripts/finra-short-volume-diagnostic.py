import json, math, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import pandas as pd
from scipy.stats import spearmanr

BASE='https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt'
root=Path('.')
u=json.loads((root/'data/universe-history.json').read_text())['history']
u=sorted([x for x in u if '2020-01-01'<=x['asOf']<='2026-08-25'], key=lambda x:x['asOf'])
market=json.loads((root/'public/data/market-data.json').read_text())['histories']
qqq=market['QQQ']
qdates=[x['date'] for x in qqq]
qidx={d:i for i,d in enumerate(qdates)}
syms=sorted({m['symbol'] for x in u for m in x['symbols']})
aliases={'BRK-B':'BRK.B'}
wanted={aliases.get(s,s):s for s in syms}

# Predeclared: use the 20 completed US sessions BEFORE the monthly signal date.
needed=set()
windows={}
for x in u:
    d=x['asOf']
    i=qidx.get(d)
    if i is None or i<20: continue
    ds=qdates[i-20:i]
    windows[d]=ds
    needed.update(ds)

def fetch_day(d):
    ymd=d.replace('-','')
    req=Request(BASE.format(ymd), headers={'User-Agent':'momentum-research/1.0 contact=research'})
    try:
        with urlopen(req, timeout=30) as r:
            text=r.read().decode('utf-8','replace')
    except (HTTPError, URLError, TimeoutError) as e:
        return d, None, str(e)
    rows={}
    lines=text.splitlines()
    if not lines or 'Symbol' not in lines[0]: return d,None,'invalid-header'
    for line in lines[1:]:
        p=line.split('|')
        if len(p)<5: continue
        sym=p[1]
        if sym not in wanted: continue
        try: sv=float(p[2]); tv=float(p[4])
        except: continue
        if tv>0: rows[wanted[sym]]=(sv,tv)
    return d,rows,None

byday={}; errors=[]
with ThreadPoolExecutor(max_workers=24) as ex:
    futs={ex.submit(fetch_day,d):d for d in sorted(needed)}
    for j,f in enumerate(as_completed(futs),1):
        d,rows,err=f.result()
        if rows is not None: byday[d]=rows
        else: errors.append((d,err))
        if j%250==0: print('FINRA_FETCH',j,'/',len(futs),'ok',len(byday),'err',len(errors), flush=True)

def future(arr,signal,n):
    ds=[p['date'] for p in arr]
    try:i=ds.index(signal)
    except ValueError:return None
    if i+1>=len(arr) or i+n>=len(arr):return None
    e=arr[i+1].get('open') or arr[i+1].get('close'); z=arr[i+n].get('close')
    return z/e-1 if e and z and e>0 else None

def ratio(symbol,ds):
    sv=tv=0.0; n=0
    for d in ds:
        row=byday.get(d,{}).get(symbol)
        if row:
            sv+=row[0]; tv+=row[1]; n+=1
    return (sv/tv if tv>0 and n>=15 else None),n
obs=[]
for x in u:
    d=x['asOf']; ds=windows.get(d)
    if not ds: continue
    for m in x['symbols']:
        s=m['symbol']; arr=market.get(s)
        if not arr: continue
        r,n=ratio(s,ds); r21=future(arr,d,21); r63=future(arr,d,63)
        if r21 is None or r63 is None: continue
        obs.append({'date':d,'symbol':s,'shortRatio20':r,'finraDays':n,'r21':r21,'r63':r63})

df=pd.DataFrame(obs)

def monthly_ic(frame,target):
    vals=[]
    for _,g in frame.groupby('date'):
        z=g[['shortRatio20',target]].dropna()
        if len(z)>=8 and z.shortRatio20.nunique()>1 and z[target].nunique()>1:
            r=spearmanr(z.shortRatio20,z[target]).statistic
            if pd.notna(r): vals.append(float(r))
    return (sum(vals)/len(vals) if vals else None),len(vals)

def spread(frame,target):
    spreads=[]
    for _,g in frame.groupby('date'):
        z=g[['shortRatio20',target]].dropna().sort_values('shortRatio20')
        if len(z)<8: continue
        q=max(2,len(z)//4)
        spreads.append(float(z.tail(q)[target].mean()-z.head(q)[target].mean()))
    return (sum(spreads)/len(spreads) if spreads else None),len(spreads)

def summ(frame):
    ic21,n21=monthly_ic(frame,'r21');ic63,n63=monthly_ic(frame,'r63')
    sp21,s21=spread(frame,'r21');sp63,s63=spread(frame,'r63')
    return {'observations':len(frame),'coverage':float(frame.shortRatio20.notna().mean()) if len(frame) else None,
            'meanMonthlyIC21':ic21,'icMonths21':n21,'meanMonthlyIC63':ic63,'icMonths63':n63,
            'meanMonthlyHighMinusLow21':sp21,'spreadMonths21':s21,'meanMonthlyHighMinusLow63':sp63,'spreadMonths63':s63}

early=df[(df.date>='2020-01-01')&(df.date<='2023-12-31')]
late=df[(df.date>='2024-01-01')&(df.date<='2026-08-25')]
out={'validity':{'researchOnly':True,'trueOOS':False,'parameterSearch':False,
    'hypothesis':'Higher prior-20-session FINRA consolidated short-sale volume ratio predicts lower subsequent return.',
    'pit':'Uses only the 20 completed US sessions strictly before signal date; future starts next open.',
    'dataNote':'FINRA short-sale volume is transaction volume, not reported short interest.'},
    'coverage':{'dynamicSymbols':len(syms),'requiredDates':len(needed),'downloadedDates':len(byday),'downloadErrors':len(errors)},
    'early2020_2023':summ(early),'late2024_2026':summ(late)}
print(json.dumps(out,indent=2))
p=root/'data/research/finra-short-volume-diagnostic';p.mkdir(parents=True,exist_ok=True);(p/'result.json').write_text(json.dumps(out,indent=2))
