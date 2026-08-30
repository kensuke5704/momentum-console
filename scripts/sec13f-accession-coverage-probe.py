# research rerun: trigger dedicated accession PIT recovery probe
import duckdb, json
BASE='https://huggingface.co/datasets/zalizedata/us-public-company-financials-dataset/resolve/main/data'
FIL=[f'{BASE}/filings/filings-0000{i}-of-00003.parquet?download=true' for i in range(3)]
H=[f'{BASE}/institutional_holdings/institutional_holdings-0000{i}-of-00002.parquet?download=true' for i in range(2)]
con=duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
fr='read_parquet(['+','.join("'"+u+"'" for u in FIL)+'])'; hr='read_parquet(['+','.join("'"+u+"'" for u in H)+'])'
q=f'''WITH h AS (
 SELECT accession, manager_cik, CAST(period_of_report AS DATE) period_of_report, filed_at
 FROM {hr}
 WHERE CAST(period_of_report AS DATE) BETWEEN DATE '2020-01-01' AND DATE '2026-08-25'
), f AS (
 SELECT accession, cik, CAST(filed_at AS DATE) filing_date, form_type
 FROM {fr}
 WHERE form_type IN ('13F-HR','13F-HR/A')
)
SELECT year(period_of_report) y,
 count(*) holding_rows,
 count(DISTINCT h.accession) holding_accessions,
 count(*) FILTER (WHERE f.accession IS NOT NULL) matched_rows,
 count(DISTINCT h.accession) FILTER (WHERE f.accession IS NOT NULL) matched_accessions,
 count(*) FILTER (WHERE h.filed_at IS NULL) missing_native_filed_rows,
 count(*) FILTER (WHERE h.filed_at IS NULL AND f.filing_date IS NOT NULL) recovered_rows,
 min(f.filing_date) min_recovered_filed,
 max(f.filing_date) max_recovered_filed
FROM h LEFT JOIN f USING(accession)
GROUP BY 1 ORDER BY 1'''
rows=con.execute(q).fetchall()
samp=con.execute(f'''SELECT h.accession,h.manager_cik,h.period_of_report,h.filed_at native_filed,f.filing_date,f.cik,f.form_type,h.issuer_name,h.cusip
FROM {hr} h JOIN (SELECT accession,cik,CAST(filed_at AS DATE) filing_date,form_type FROM {fr} WHERE form_type IN ('13F-HR','13F-HR/A')) f USING(accession)
WHERE CAST(h.period_of_report AS DATE) BETWEEN DATE '2020-01-01' AND DATE '2020-12-31' AND h.filed_at IS NULL LIMIT 10''').fetchall()
print(json.dumps({'byYear':rows,'samplesRecovered2020':samp},default=str,indent=2))
