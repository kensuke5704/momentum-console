import duckdb, json
BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/filings'
# Probe dataset layout using wildcard parquet path exposed by HF resolve.
URL=f'{BASE}/filings-*.parquet?download=true'
con=duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
try:
    schema=con.execute(f"DESCRIBE SELECT * FROM read_parquet('{URL}')").fetchall()
    sample=con.execute(f"SELECT * FROM read_parquet('{URL}') WHERE upper(form_type) LIKE 'SC 13%' LIMIT 10").fetchall()
    print(json.dumps({'schema':schema,'sample13':sample},default=str,indent=2))
except Exception as e:
    print(json.dumps({'error':str(e)},indent=2)); raise
