import duckdb, json

BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/institutional_holdings'
URLS=[
 f'{BASE}/institutional_holdings-00000-of-00002.parquet?download=true',
 f'{BASE}/institutional_holdings-00001-of-00002.parquet?download=true',
]
con=duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
rel='read_parquet([' + ','.join("'"+u+"'" for u in URLS) + '])'
print(json.dumps({'schema': con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchall()}, default=str, indent=2))
print('SAMPLE')
rows=con.execute(f"SELECT * FROM {rel} LIMIT 5").fetchall()
print(json.dumps(rows, default=str, indent=2))
