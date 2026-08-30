import json, re, math
from pathlib import Path
import duckdb
import pandas as pd
from scipy.stats import spearmanr

BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data'
CHG=f'{BASE}/holdings_changes/holdings_changes-00000-of-00001.parquet?download=true'
COMP=f'{BASE}/companies/companies-00000-of-00001.parquet?download=true'
HOLD=[f'{BASE}/institutional_holdings/institutional_holdings-00000-of-00002.parquet?download=true',f'{BASE}/institutional_holdings/institutional_holdings-00001-of-00002.parquet?download=true']

def norm(s):
    s=(s or '').upper().replace('&',' AND ')
    s=re.sub(r'[^A-Z0-9 ]+',' ',s)
    toks=[x for x in s.split() if x not in {'INC','INCORPORATED','CORP','CORPORATION','CO','COMPANY','LTD','LIMITED','PLC','NEW','THE'}]
    aliases={'LABS':'LABORATORIES','TECHNOLOGIES':'TECHNOLOGY'}
    toks=[aliases.get(x,x) for x in toks]
    return ''.join(toks)

def future_ret(hist, signal_date, n):
    rows=[x for x in hist if x['date']>signal_date and x.get('open') and x.get('close')]
    if len(rows)<n: return None
    return rows[n-1]['close']/rows[0]['open']-1

def mean_ic(df, col):
    vals=[]
    for _,g in df.groupby('date'):
        z=g[['breadth',col]].dropna()
        if len(z)>=4 and z.breadth.nunique()>1 and z[col].nunique()>1:
            r=spearmanr(z.breadth,z[col]).statistic
            if pd.notna(r): vals.append(float(r))
    return sum(vals)/len(vals) if vals else None, len(vals)

def quartile_spread(df,col):
    z=df[['breadth',col]].dropna().sort_values('breadth')
    if len(z)<8:return None
    q=max(1,len(z)//4)
    return float(z.tail(q)[col].mean()-z.head(q)[col].mean())

def summarize(df):
    ic21,n21=mean_ic(df,'r21'); ic63,n63=mean_ic(df,'r63')
    return {'observations':len(df),'coverage':float(df.breadth.notna().mean()) if len(df) else None,
            'meanMonthlyIC21':ic21,'icMonths21':n21,'meanMonthlyIC63':ic63,'icMonths63':n63,
            'topBottomSpread21':quartile_spread(df,'r21'),'topBottomSpread63':quartile_spread(df,'r63')}

root=Path('.')
top=json.loads((root/'data/research/production-top10-monthly/result.json').read_text())
market=json.loads((root/'public/data/market-data.json').read_text())['histories']
symbols=sorted(set(x['symbol'] for m in top['monthly'] for x in m['top10']))

con=duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
# Identity map uses deterministic high-confidence normalized exact company-name matches only.
comp=con.execute(f"SELECT ticker, company_name FROM read_parquet('{COMP}') WHERE ticker IS NOT NULL").df()
comp['norm']=comp.company_name.map(norm)
comp=comp[comp.ticker.isin(symbols)]
counts=comp.groupby('norm').ticker.nunique()
unique=set(counts[counts==1].index)
mapdf=comp[comp['norm'].isin(unique)][['norm','ticker']].drop_duplicates('norm')
con.register('mapdf',mapdf)

holds="read_parquet(["+','.join("'"+u+"'" for u in HOLD)+'])'
# One public date per manager/report period from original 13F-HR only; amendments excluded.
con.execute(f"""CREATE TEMP TABLE filing_dates AS
SELECT manager_cik, period_of_report, min(CAST(filed_at AS DATE)) filed_date
FROM {holds}
WHERE submission_type='13F-HR' AND filed_at IS NOT NULL
GROUP BY 1,2""")
# Normalize SEC issuer names with same conservative transformation in Python after pulling only matched candidates.
# Pull changes for relevant calendar window, then high-confidence exact normalized mapping in pandas.
chg=con.execute(f"""SELECT c.manager_cik,c.issuer_name,c.period_cur,c.action,f.filed_date
FROM read_parquet('{CHG}') c
JOIN filing_dates f ON f.manager_cik=c.manager_cik AND f.period_of_report=c.period_cur
WHERE c.period_cur>='2019-09-30' AND c.period_cur<='2026-06-30'
  AND c.action IN ('increase','new','decrease','exit','unchanged')""").df()
chg['norm']=chg.issuer_name.map(norm)
name_to_ticker=dict(zip(mapdf['norm'],mapdf['ticker']))
chg['ticker']=chg['norm'].map(name_to_ticker)
chg=chg[chg.ticker.notna()].copy()
chg['sign']=chg.action.map({'increase':1,'new':1,'decrease':-1,'exit':-1,'unchanged':0}).fillna(0)
chg['filed_date']=pd.to_datetime(chg.filed_date)

obs=[]
for m in top['monthly']:
    d=m['date']
    if d<'2020-01-01' or d>'2026-08-25': continue
    dt=pd.Timestamp(d)
    for item in m['top10']:
        s=item['symbol']; h=market.get(s,[])
        sub=chg[(chg.ticker==s)&(chg.filed_date<=dt)]
        breadth=None; managers=0
        if len(sub):
            # latest public change per manager as of signal close
            latest=sub.sort_values(['manager_cik','filed_date']).groupby('manager_cik').tail(1)
            managers=len(latest); breadth=float(latest.sign.mean()) if managers else None
        obs.append({'date':d,'symbol':s,'breadth':breadth,'managerCount':managers,
                    'r21':future_ret(h,d,21),'r63':future_ret(h,d,63)})

df=pd.DataFrame(obs)
early=df[(df.date>='2020-01-01')&(df.date<='2023-12-31')]
late=df[(df.date>='2024-01-01')&(df.date<='2026-08-25')]
result={'validity':{'researchOnly':True,'trueOOS':False,'parameterSearch':False,
        'hypothesis':'higher PIT 13F cross-manager accumulation breadth predicts higher subsequent returns',
        'pit':'Only original 13F-HR manager/report changes with filing date <= signal close; latest public change per manager.',
        'identityMapping':'Normalized exact unique SEC company-name match only; no fuzzy matching.'},
        'coverage':{'productionTop10Union':len(symbols),'mappedCompanyTickers':int(mapdf.ticker.nunique()),
                    'mappedChangeTickers':int(chg.ticker.nunique()),'changeRows':len(chg)},
        'early2020_2023':summarize(early),'late2024_2026':summarize(late)}
print(json.dumps(result,indent=2))
out=root/'data/research/sec13f-accumulation-diagnostic'; out.mkdir(parents=True,exist_ok=True)
(out/'result.json').write_text(json.dumps(result,indent=2))
