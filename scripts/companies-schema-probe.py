import duckdb, json
URL='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/companies/companies-00000-of-00001.parquet?download=true'
con=duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs;")
print(json.dumps({'schema': con.execute(f"DESCRIBE SELECT * FROM read_parquet('{URL}')").fetchall()}, default=str, indent=2))
print(json.dumps(con.execute(f"SELECT * FROM read_parquet('{URL}') LIMIT 10").fetchall(), default=str, indent=2))
