import json, os, subprocess, sys, urllib.request
from pathlib import Path

BASE='https://huggingface.co/datasets/ttchopper/openfundex/resolve/main/'
FILES=['validation.parquet','test.parquet','recent.parquet']
D=Path('/tmp/openfundex'); D.mkdir(exist_ok=True)
for f in FILES:
    p=D/f
    if not p.exists():
        print('DOWNLOAD',f,flush=True)
        urllib.request.urlretrieve(BASE+f+'?download=true',p)
        print('BYTES',f,p.stat().st_size,flush=True)
try:
    import duckdb
except Exception:
    subprocess.check_call([sys.executable,'-m','pip','install','duckdb==1.4.0','-q'])
    import duckdb
con=duckdb.connect()
paths=','.join("'"+str(D/f)+"'" for f in FILES)
q=f"""
select cik,ticker,company_name,adsh,fiscal_year,fiscal_quarter,filing_date,period_end_date,
       revenue,operating_income,operating_margin,qa_pass,source_file
from read_parquet([{paths}], union_by_name=true)
where (upper(ticker) in ('NVDA','GOOG','GOOGL') or cik in (1045810,1652044))
  and filing_date >= date '2025-01-01'
order by filing_date desc
limit 40
"""
rows=con.execute(q).fetchdf().to_dict('records')
for r in rows:
    for k,v in list(r.items()):
        if hasattr(v,'isoformat'): r[k]=v.isoformat()
        elif str(type(v)).startswith("<class 'numpy."): r[k]=v.item()
print('SAMPLE_JSON')
print(json.dumps(rows,indent=2,default=str))
# Coverage using Top10 union generated with the existing TS script in the workflow.
p=Path('data/research/sec-top10-union/result.json')
if p.exists():
    union=json.loads(p.read_text())['symbols']
    con.execute('create temp table wanted(ticker varchar)')
    con.executemany('insert into wanted values (?)',[(x.upper(),) for x in union])
    cov=con.execute(f"""
      with d as (select distinct upper(ticker) ticker from read_parquet([{paths}], union_by_name=true)
                 where filing_date between date '2020-01-01' and date '2026-08-25')
      select count(*) wanted, count(d.ticker) covered from wanted w left join d using(ticker)
    """).fetchone()
    missing=[x[0] for x in con.execute(f"""
      with d as (select distinct upper(ticker) ticker from read_parquet([{paths}], union_by_name=true)
                 where filing_date between date '2020-01-01' and date '2026-08-25')
      select w.ticker from wanted w left join d using(ticker) where d.ticker is null order by 1
    """).fetchall()]
    print('COVERAGE',cov[0],cov[1],cov[1]/cov[0] if cov[0] else None)
    print('MISSING',','.join(missing))
