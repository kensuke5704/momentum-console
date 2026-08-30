import subprocess,sys,json
try: import duckdb
except Exception:
 subprocess.check_call([sys.executable,'-m','pip','install','duckdb==1.4.0','-q']); import duckdb
url='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/insider_transactions/insider_transactions-00000-of-00001.parquet?download=true'
con=duckdb.connect(); con.execute('INSTALL httpfs'); con.execute('LOAD httpfs')
print('SCHEMA',con.execute(f"describe select * from read_parquet('{url}')").fetchall())
print('SAMPLE',json.dumps(con.execute(f"select * from read_parquet('{url}') limit 3").fetchall(),default=str))
