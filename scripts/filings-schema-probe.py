import duckdb, json
BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/filings'
URLS=[f'{BASE}/filings-0000{i}-of-00003.parquet?download=true' for i in range(3)]
rel='read_parquet(['+','.join("'"+u+"'" for u in URLS)+'])'
con=duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
try:
    schema=con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchall()
    sample=con.execute(f"SELECT * FROM {rel} WHERE upper(form_type) LIKE 'SC 13%' LIMIT 10").fetchall()
    print(json.dumps({'schema':schema,'sample13':sample},default=str,indent=2))
except Exception as e:
    print(json.dumps({'error':str(e)},indent=2)); raise
