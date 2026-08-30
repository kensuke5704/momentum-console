import duckdb, json
BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/institutional_holdings'
URLS=[f'{BASE}/institutional_holdings-00000-of-00002.parquet?download=true',f'{BASE}/institutional_holdings-00001-of-00002.parquet?download=true']
rel='read_parquet(['+','.join("'"+u+"'" for u in URLS)+'])'
con=duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
out={}
out['range']=con.execute(f"SELECT min(period_of_report),max(period_of_report),min(filed_at),max(filed_at),count(*) FROM {rel}").fetchone()
out['byYear']=con.execute(f"SELECT substr(period_of_report,1,4) y,count(*) n,count(distinct manager_cik) managers FROM {rel} GROUP BY 1 ORDER BY 1").fetchall()
print(json.dumps(out,default=str,indent=2))
