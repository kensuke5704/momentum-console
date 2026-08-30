import duckdb, json
BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data'
FIL=[f'{BASE}/filings/filings-0000{i}-of-00003.parquet?download=true' for i in range(3)]
H=[f'{BASE}/institutional_holdings/institutional_holdings-0000{i}-of-00002.parquet?download=true' for i in range(2)]
con=duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
fr='read_parquet(['+','.join("'"+u+"'" for u in FIL)+'])'
hr='read_parquet(['+','.join("'"+u+"'" for u in H)+'])'
fs=con.execute(f'DESCRIBE SELECT * FROM {fr}').fetchall(); hs=con.execute(f'DESCRIBE SELECT * FROM {hr}').fetchall()
fc=[x[0] for x in fs]; hc=[x[0] for x in hs]
forms=con.execute(f"SELECT form_type, count(*) n, min(CAST(filed_at AS DATE)) mn, max(CAST(filed_at AS DATE)) mx FROM {fr} WHERE upper(form_type) LIKE '13F%' GROUP BY 1 ORDER BY n DESC").fetchall()
fsel=[c for c in ['cik','form_type','filed_at','accession','period_of_report','report_date','period_cur'] if c in fc]
hsel=[c for c in ['manager_cik','cik','period_cur','filed_at','accession','issuer_name','cusip'] if c in hc]
fsamp=con.execute(f"SELECT {','.join(fsel)} FROM {fr} WHERE upper(form_type) LIKE '13F%' AND CAST(filed_at AS DATE) BETWEEN DATE '2020-01-01' AND DATE '2021-12-31' LIMIT 10").fetchall() if fsel else []
hsamp=con.execute(f"SELECT {','.join(hsel)} FROM {hr} WHERE period_cur BETWEEN DATE '2020-01-01' AND DATE '2021-12-31' LIMIT 10").fetchall() if hsel and 'period_cur' in hc else []
print(json.dumps({'filingColumns':fc,'holdingColumns':hc,'forms13f':forms,'filingSampleColumns':fsel,'filingSamples2020_21':fsamp,'holdingSampleColumns':hsel,'holdingSamples2020_21':hsamp},default=str,indent=2))
