import duckdb, json

URL='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/institutional_holdings/institutional_holdings-00000-of-00001.parquet?download=true'
con=duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
print(json.dumps({'schema': con.execute(f"DESCRIBE SELECT * FROM read_parquet('{URL}')").fetchall()}, default=str, indent=2))
print('SAMPLE')
rows=con.execute(f"SELECT * FROM read_parquet('{URL}') LIMIT 5").fetchall()
print(json.dumps(rows, default=str, indent=2))
