import json
from pathlib import Path
from bisect import bisect_right
import duckdb

ROOT=Path('.')
BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data'
FILINGS=[f'{BASE}/filings/filings-0000{i}-of-00003.parquet?download=true' for i in range(3)]
COMP=f'{BASE}/companies/companies-00000-of-00001.parquet?download=true'

market=json.loads((ROOT/'public/data/market-data.json').read_text())['histories']
uh=json.loads((ROOT/'data/universe-history.json').read_text())['history']
uh=sorted(uh,key=lambda x:x['asOf'])
uh_dates=[x['asOf'] for x in uh]

# Exact issuer CIK -> ticker mapping; retain only unique ticker per CIK.
con=duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
rel='read_parquet(['+','.join("'"+u+"'" for u in FILINGS)+'])'
companies=con.execute(f"SELECT cik, upper(ticker) ticker FROM read_parquet('{COMP}') WHERE cik IS NOT NULL AND ticker IS NOT NULL").fetchall()
by_cik={}
for cik,t in companies: by_cik.setdefault(int(cik),set()).add(t)
cik_to_ticker={cik:next(iter(ts)) for cik,ts in by_cik.items() if len(ts)==1}

rows=con.execute(f"""
SELECT cik, CAST(filed_at AS DATE) filed_date, accession
FROM {rel}
WHERE form_type='SC 13D'
  AND CAST(filed_at AS DATE)>=DATE '2020-01-01'
  AND CAST(filed_at AS DATE)<=DATE '2026-08-25'
  AND cik IS NOT NULL
ORDER BY filed_date, cik, accession
""").fetchall()

# de-dupe exact same issuer/date; multiple accessions on one date are one public event for return measurement.
events=[]; seen=set()
for cik,fd,acc in rows:
    key=(int(cik),str(fd))
    if key in seen: continue
    seen.add(key)
    ticker=cik_to_ticker.get(int(cik))
    if ticker and ticker in market:
        events.append((ticker,str(fd)))

def latest_universe_before(d):
    i=bisect_right(uh_dates,d)-1
    return uh[i] if i>=0 else None

def future_from_after_filing(symbol, filed, n):
    arr=market.get(symbol,[])
    fut=[p for p in arr if p['date']>filed and p.get('open') and p.get('close')]
    if len(fut)<n: return None
    return fut[n-1]['close']/fut[0]['open']-1

def median(xs):
    xs=sorted(xs)
    if not xs:return None
    m=len(xs)//2
    return xs[m] if len(xs)%2 else (xs[m-1]+xs[m])/2

def benchmark(u,filed,n):
    vals=[]
    for m in u['symbols']:
        r=future_from_after_filing(m['symbol'],filed,n)
        if r is not None: vals.append(r)
    return median(vals) if len(vals)>=10 else None

obs=[]
for ticker,filed in events:
    u=latest_universe_before(filed)
    if not u or ticker not in {m['symbol'] for m in u['symbols']}: continue
    r21=future_from_after_filing(ticker,filed,21); r63=future_from_after_filing(ticker,filed,63)
    b21=benchmark(u,filed,21); b63=benchmark(u,filed,63)
    if None in (r21,r63,b21,b63): continue
    obs.append({'ticker':ticker,'filedDate':filed,'universeAsOf':u['asOf'],'r21':r21,'r63':r63,'bench21':b21,'bench63':b63,'abn21':r21-b21,'abn63':r63-b63})

def mean(xs): return sum(xs)/len(xs) if xs else None
def summ(start,end):
    x=[o for o in obs if start<=o['filedDate']<=end]
    return {'events':len(x),
      'meanR21':mean([o['r21'] for o in x]),'medianR21':median([o['r21'] for o in x]),
      'meanR63':mean([o['r63'] for o in x]),'medianR63':median([o['r63'] for o in x]),
      'meanAbn21':mean([o['abn21'] for o in x]),'medianAbn21':median([o['abn21'] for o in x]),
      'meanAbn63':mean([o['abn63'] for o in x]),'medianAbn63':median([o['abn63'] for o in x]),
      'positiveAbn21Share':mean([1.0 if o['abn21']>0 else 0.0 for o in x]),
      'positiveAbn63Share':mean([1.0 if o['abn63']>0 else 0.0 for o in x])}

out={'validity':{'researchOnly':True,'trueOOS':False,'parameterSearch':False,
  'hypothesis':'Fresh non-amended Schedule 13D filings for PIT-dynamic-universe securities are followed by positive 21/63-session abnormal returns versus the contemporaneous dynamic-universe median.',
  'forms':'SC 13D only; SC 13D/A and all 13G forms excluded before observing returns.',
  'pit':'Issuer filing date must be known; event return begins at first US trading-session open strictly after filed_date; benchmark uses latest universe snapshot at/before filing date.',
  'identity':'Exact unique issuer CIK to ticker mapping only.'},
  'coverage':{'raw13dRows':len(rows),'mappedCandidateEvents':len(events),'eligiblePITEvents':len(obs)},
  'early2020_2023':summ('2020-01-01','2023-12-31'),
  'late2024_2026':summ('2024-01-01','2026-08-25'),
  'events':obs}
print(json.dumps({k:v for k,v in out.items() if k!='events'},indent=2))
p=ROOT/'data/research/sec13d-event-diagnostic';p.mkdir(parents=True,exist_ok=True);(p/'result.json').write_text(json.dumps(out,indent=2))
