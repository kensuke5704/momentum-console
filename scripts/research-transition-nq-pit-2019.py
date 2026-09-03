#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-nq-pit-2019.json'
sspec=importlib.util.spec_from_file_location('seg',ROOT/'scripts'/'research-nq-series-segmentation-2006.py');seg=importlib.util.module_from_spec(sspec);sspec.loader.exec_module(seg)
SOURCES=[
 {'cik':'1329377','company':'FIRST TRUST EXCHANGE-TRADED FUND','accession':'0001445546-18-005192','primary':'etf1_nq.htm','targets':['S000010977','S000017177','S000017178']},
 {'cik':'1364608','company':'FIRST TRUST EXCHANGE-TRADED FUND II','accession':'0001445546-19-001205','primary':'etf2_nq.htm','targets':['S000033237','S000050385']},
 {'cik':'1552740','company':'FIRST TRUST EXCHANGE-TRADED FUND VI','accession':'0001445546-19-001208','primary':'etf6_nq.htm','targets':['S000053942','S000053943','S000053944','S000053945','S000053946','S000053947','S000053948']},
 {'cik':'1552740','company':'FIRST TRUST EXCHANGE-TRADED FUND VI','accession':'0001445546-19-001184','primary':'etf6_nq.htm','targets':['S000044209']},
 {'cik':'1467831','company':'ETF MANAGERS TRUST','accession':'0000894189-19-001075','primary':'etfmg_nq.htm','targets':['S000047480','S000050191']},
 {'cik':'1408970','company':'ADVISORSHARES TRUST','accession':'0001615774-18-012797','primary':'s113544_nq.htm','targets':['S000031813','S000055090','S000059263']},
]
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
REPORT_DATE=re.compile(r'(?:Period of Report|CONFORMED PERIOD OF REPORT[:\s]+)\s*(\d{4}[-/]?\d{2}[-/]?\d{2}|\d{8})',re.I)
FILING_DATE=re.compile(r'(?:Filing Date|FILED AS OF DATE[:\s]+)\s*(\d{4}[-/]?\d{2}[-/]?\d{2}|\d{8})',re.I)
COUNTRY=re.compile(r'^\s*([A-Za-z][A-Za-z .&()-]+?)\s+[—–-]\s*\d+(?:\.\d+)?%\s*$')
COMMON=re.compile(r'COMMON\s+STOCKS?',re.I)
NONCOMMON=re.compile(r'MONEY MARKET|REPURCHASE|PREFERRED|BONDS?|NOTES?|TOTAL INVESTMENTS|NET ASSETS',re.I)
NUM=re.compile(r'^\$?\(?\d[\d,]*(?:\.\d+)?\)?$')
def iso(v):
 d=re.sub(r'\D','',v or '')
 return f'{d[:4]}-{d[4:6]}-{d[6:8]}' if len(d)>=8 else None
def base(s):return f'https://www.sec.gov/Archives/edgar/data/{int(s["cik"])}/{s["accession"].replace("-","")}'
def header_url(s):return f'{base(s)}/{s["accession"]}-index-headers.html'
def primary_url(s):return f'{base(s)}/{s["primary"]}'
def get(url,timeout=45):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:raw=r.read(4_000_000)
   return u,raw.decode('utf-8','replace')
  except Exception as e:last=e
 raise last or RuntimeError('fetch failed')
def clean(x):return ' '.join(x.replace('\xa0',' ').replace('\u2002',' ').split())
def number(x):
 x=clean(x).replace('$','').replace(',','')
 neg=x.startswith('(') and x.endswith(')')
 if neg:x=x[1:-1]
 try:v=float(x)
 except:return None
 return -v if neg else v
def parse_2019_common(block):
 holdings=[];in_common=False;country=None
 for raw in block.splitlines():
  line=clean(raw)
  if not line:continue
  if COMMON.search(line) and not line.upper().startswith('TOTAL '):
   in_common=True
   m=COUNTRY.match(line)
   if m:country=m.group(1).strip()
   continue
  if in_common and NONCOMMON.search(line):
   in_common=False;country=None;continue
  if not in_common:continue
  cm=COUNTRY.match(line)
  if cm:
   country=cm.group(1).strip();continue
  parts=[clean(p) for p in raw.replace('\xa0',' ').replace('\u2002',' ').split('\t')]
  parts=[p for p in parts if p and p!='$']
  if len(parts)<3 or not NUM.match(parts[0]) or not NUM.match(parts[-1]):continue
  qty=number(parts[0]);value=number(parts[-1]);desc=' '.join(parts[1:-1]).strip()
  if qty is None or qty<=0 or value is None or value<=0 or len(desc)<2:continue
  if re.search(r'^(TOTAL|COST\b)',desc,re.I):continue
  holdings.append({'description':desc,'quantityOrPrincipal':qty,'marketValue':value,'countrySection':country,'assetSection':'COMMON_EQUITY'})
 total=sum(h['marketValue'] for h in holdings)
 if total>0:
  for h in holdings:h['weight']=100*h['marketValue']/total
  holdings.sort(key=lambda h:h['weight'],reverse=True)
 return holdings,total

def main():
 records=[];audits=[]
 for s in SOURCES:
  try:
   meta_transport,header=get(header_url(s));rm=REPORT_DATE.search(header);fm=FILING_DATE.search(header);report=iso(rm.group(1) if rm else None);filed=iso(fm.group(1) if fm else None)
   series=seg.meta.parse_series_contracts(header,s['company']);by={x.get('seriesId'):x for x in series if x.get('seriesId')}
   body_transport,text=get(primary_url(s));grouped,assignment=seg.grouped_schedule_blocks(text,list(by.values()))
   source_rows=[]
   for sid in s['targets']:
    meta=by.get(sid);blocks=grouped.get(sid,[])
    if not meta or not blocks:
     row={'seriesId':sid,'status':'UNASSIGNED','metadataPresent':bool(meta),'schedulePages':len(blocks)};source_rows.append(row);print('UNASSIGNED',json.dumps(row),flush=True);continue
    holdings,total=parse_2019_common('\n'.join(blocks));top10=sum(h.get('weight',0) for h in holdings[:10]);usable=bool(seg.eligible_name(meta.get('seriesName') or '') and 10<=len(holdings)<=120 and total>0 and top10>=25)
    countries=sorted(set(h.get('countrySection') for h in holdings if h.get('countrySection')))
    r={'accession':s['accession'],'cik':s['cik'],'registrant':s['company'],'form':'N-Q','filingDate':filed,'reportDate':report,'headerUrl':header_url(s),'primaryDocument':s['primary'],'primaryUrl':primary_url(s),'seriesId':sid,'seriesName':meta.get('seriesName'),'fundTickers':meta.get('etfTickers',[]),'schedulePages':len(blocks),'parseMethod':'TAB_COMMON_EQUITY_2019','parsedMarketValueTotal':total,'holdingCount':len(holdings),'top10Weight':top10,'countrySections':countries,'structurallyUsable':usable,'holdings':holdings}
    records.append(r);row={k:r[k] for k in ('seriesId','seriesName','fundTickers','schedulePages','holdingCount','top10Weight','countrySections','structurallyUsable')};source_rows.append(row);print('SERIES',json.dumps({**row,'topHoldings':[h['description'] for h in holdings[:5]]}),flush=True)
   audits.append({'accession':s['accession'],'cik':s['cik'],'metadataTransport':meta_transport,'bodyTransport':body_transport,'reportDate':report,'filingDate':filed,'primaryDocument':s['primary'],'bodyChars':len(text),'registeredSeries':len(series),'scheduleMarkers':len(assignment),'assignedMarkers':sum(1 for a in assignment if a.get('seriesId')),'targets':source_rows})
  except Exception as e:audits.append({**s,'error':repr(e)});print('FAIL',s['accession'],repr(e),flush=True)
 target_count=sum(len(s['targets']) for s in SOURCES)
 out={'purpose':'Gate B actual legacy-source PIT extraction from fixed transition N-Q filings. 2019 parser reads only numeric security rows while inside explicit COMMON STOCKS sections and preserves explicit country headings. Filing selection and target series were frozen before holdings inspection.','targetSeries':target_count,'extractedSeries':len(records),'structurallyUsableSeries':sum(r['structurallyUsable'] for r in records),'records':records,'sourceAudits':audits}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('records','sourceAudits')}),flush=True)
if __name__=='__main__':main()
