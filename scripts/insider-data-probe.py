import json, subprocess, sys, urllib.request
from pathlib import Path
URL='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/insider_signal_events/insider_signal_events-00000-of-00001.parquet?download=true'
p=Path('/tmp/insider_signal_events.parquet'); urllib.request.urlretrieve(URL,p); print('BYTES',p.stat().st_size)
try: import duckdb
except Exception:
 subprocess.check_call([sys.executable,'-m','pip','install','duckdb==1.4.0','-q']); import duckdb
con=duckdb.connect(); print('SCHEMA',con.execute(f"describe select * from read_parquet('{p}')").fetchall()); print('SAMPLE',json.dumps(con.execute(f"select * from read_parquet('{p}') limit 5").fetchall(),default=str))
