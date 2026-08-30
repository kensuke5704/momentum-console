import subprocess,sys
try: import duckdb
except Exception:
 subprocess.check_call([sys.executable,'-m','pip','install','duckdb==1.4.0','-q']); import duckdb
URL='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data/insider_transactions/insider_transactions-00000-of-00001.parquet?download=true'
con=duckdb.connect(); con.execute('INSTALL httpfs'); con.execute('LOAD httpfs')
base=f"read_parquet('{URL}')"
queries={
'all_2020_26':f"select count(*) from {base} where cast(filed_at as date) between date '2020-01-01' and date '2026-08-25'",
'form4':f"select count(*) from {base} where form_type='4' and cast(filed_at as date) between date '2020-01-01' and date '2026-08-25'",
'P':f"select count(*) from {base} where form_type='4' and transaction_code='P' and cast(filed_at as date) between date '2020-01-01' and date '2026-08-25'",
'P_A':f"select count(*) from {base} where form_type='4' and transaction_code='P' and acquired_disposed='A' and cast(filed_at as date) between date '2020-01-01' and date '2026-08-25'",
'P_A_val':f"select count(*) from {base} where form_type='4' and transaction_code='P' and acquired_disposed='A' and coalesce(value_usd,0)>0 and cast(filed_at as date) between date '2020-01-01' and date '2026-08-25'",
'P_A_val_role':f"select count(*) from {base} where form_type='4' and transaction_code='P' and acquired_disposed='A' and coalesce(value_usd,0)>0 and (is_director is true or is_officer is true) and cast(filed_at as date) between date '2020-01-01' and date '2026-08-25'",
}
for k,q in queries.items():
 print(k, con.execute(q).fetchone()[0])
print('P sample', con.execute(f"select issuer_ticker,owner_name,filed_at,transaction_date,transaction_code,acquired_disposed,value_usd,is_director,is_officer,officer_title from {base} where form_type='4' and transaction_code='P' and cast(filed_at as date) between date '2024-01-01' and date '2026-08-25' limit 20").fetchall())
print('codes', con.execute(f"select transaction_code,acquired_disposed,count(*) n from {base} where form_type='4' and cast(filed_at as date) between date '2024-01-01' and date '2026-08-25' group by 1,2 order by n desc limit 30").fetchall())
