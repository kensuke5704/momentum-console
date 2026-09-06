#!/usr/bin/env python3
from __future__ import annotations
import html,io,json,os,re,time,urllib.request,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,application/zip,*/*','Accept-Encoding':'identity'}
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
FORM_PRIORITY={'10-K':0,'10-K/A':1,'10-Q':2,'10-Q/A':3,'8-K':4,'8-K/A':5,'DEF 14A':6,'DEFA14A':7,'PRE 14A':8,'11-K':9,'S-8':10,'S-8 POS':11}
ISSUER_FORMS=set(FORM_PRIORITY)
JURIS_RE=re.compile(r'\s*/[A-Z0-9]{2,3}/?\s*$',re.I)

def clean_issuer(s):
 s=re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$','',s or '',flags=re.I)
 return ' '.join(s.replace('’',"'").split()).strip(' .,-')

def normalize_company(s):
 s=JURIS_RE.sub('',s or '')
 s=clean_issuer(s).upper().replace('&',' AND ')
 s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b',' ',s)
 s=re.sub(r'[^A-Z0-9]+',' ',s)
 return ' '.join(s.split())

def cleaned_forms(raw):
 vals=[raw];s=raw
 pats=[r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',r'\s*/[A-Z]{2}\s*$']
 changed=True
 while changed:
  changed=False
  for p in pats:
   ns=re.sub(p,'',s,flags=re.I).strip()
   if ns!=s: vals.append(ns);s=ns;changed=True
 return list(dict.fromkeys(v for v in vals if v))

def get_text(url,limit=2_000_000,timeout=20):
 last=None
 for candidate in (url,'https://r.jina.ai/'+url):
  try:
   req=urllib.request.Request(candidate,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:
    return r.read(limit).decode('latin-1','replace'),candidate
  except Exception as e: last=e
 raise RuntimeError(repr(last))

def load_master(years):
 rows=[];transports={}
 for year in years:
  for q in range(1,5):
   base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
   text=None;tr=None
   try:
    req=urllib.request.Request(base+'/master.zip',headers=UA)
    with urllib.request.urlopen(req,timeout=35) as r:data=r.read(20_000_000)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
     name=next(n for n in z.namelist() if n.lower().endswith('master.idx'))
     text=z.read(name).decode('latin-1','replace');tr=base+'/master.zip'
   except Exception:
    text,tr=get_text(base+'/master.idx',limit=20_000_000,timeout=45)
   transports[f'{year}Q{q}']=tr
   for line in text.splitlines():
    p=line.split('|')
    if len(p)<5 or not p[0].strip().isdigit(): continue
    cik,company,form,date,filename=[x.strip() for x in p[:5]];form=form.upper()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date): continue
    rows.append({'cik':cik.zfill(10),'company':company,'normalizedCompany':normalize_company(company),'form':form,'dateFiled':date,'filename':filename})
 return rows,transports

def accession_parts(filename):
 m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',filename,re.I)
 if not m:return None
 cik=str(int(m.group(1)));acc=m.group(2);return cik,acc,acc.replace('-','')

def header_index_url(filename):
 parts=accession_parts(filename)
 if not parts:return None
 cik,acc,ad=parts
 return f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index-headers.html'

def header_page(filename):
 url=header_index_url(filename)
 if not url: raise RuntimeError('no header index url')
 return get_text(url,limit=500_000,timeout=20)

def flat_header_entity_state(target,cik,text):
 cleaned=html.unescape(re.sub(r'<[^>]*>','',text)).replace('\r','')
 nt=normalize_company(target);zcik=str(cik).zfill(10)
 blocks=re.split(r'(?im)^\s*COMPANY\s+DATA\s*:\s*$',cleaned)
 for block in blocks[1:]:
  part=re.split(r'(?im)^\s*(?:FILING\s+VALUES|BUSINESS\s+ADDRESS|MAIL\s+ADDRESS|FORMER\s+COMPANY)\s*:\s*$',block,maxsplit=1)[0]
  nm=re.search(r'(?im)^\s*COMPANY\s+CONFORMED\s+NAME\s*:\s*(.+?)\s*$',part)
  ck=re.search(r'(?im)^\s*CENTRAL\s+INDEX\s+KEY\s*:\s*(\d{1,10})\s*$',part)
  st=re.search(r'(?im)^\s*STATE\s+OF\s+INCORPORATION\s*:\s*([A-Z0-9]{2,3})\s*$',part)
  if not nm or not ck: continue
  name=nm.group(1).strip();mcik=ck.group(1).zfill(10)
  if mcik==zcik and normalize_company(name)==nt and st:return st.group(1).upper(),name
 return None,None

def filing_sort_key(r):return (FORM_PRIORITY.get(r['form'],50),-int(r['dateFiled'].replace('-','')),r['filename'])

def exact_candidates(row,master_rows):
 report=row.get('asOfReportDate');forms=[]
 for issuer in row.get('issuerVariants',[]):
  for f in cleaned_forms(str(issuer)):
   if f and f not in forms: forms.append(f)
 by=defaultdict(list);matched_forms=[]
 for form in forms:
  target=normalize_company(form)
  exact=[r for r in master_rows if r.get('form') in ISSUER_FORMS and report and r.get('dateFiled')<=report and r.get('normalizedCompany')==target]
  if exact: matched_forms.append(form)
  for r in exact: by[str(r.get('cik') or '').zfill(10)].append(r)
 if len(by)!=1:return None,[],matched_forms
 cik=next(iter(by));rows=sorted(by[cik],key=filing_sort_key);seen=set();out=[]
 for r in rows:
  fn=r.get('filename')
  if fn and fn not in seen:seen.add(fn);out.append(r)
 return cik,out,matched_forms

def main():
 shard_i=int(os.environ.get('SHARD_INDEX','0'));shard_n=int(os.environ.get('SHARD_COUNT','1'))
 data=json.loads(SRC.read_text())
 all_unknown=sorted([r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or '',r.get('asOfReportDate') or ''))
 unknown=[r for i,r in enumerate(all_unknown) if i%shard_n==shard_i]
 years=sorted({int(r['asOfReportDate'][:4]) for r in unknown if r.get('asOfReportDate')});master,transports=load_master(years)
 results=[];resolved=us=nonus=errors=0
 for i,row in enumerate(unknown):
  cik,candidates,forms=exact_candidates(row,master)
  rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'issuerVariants':row.get('issuerVariants',[]),'historicalExactCik':cik,'matchedIssuerForms':forms,'classification':'UNKNOWN','attempts':[]}
  if cik:
   for fr in candidates[:6]:
    for issuer in forms:
     try:
      text,tr=header_page(fr['filename']);st,name=flat_header_entity_state(issuer,cik,text)
      rec['attempts'].append({'form':fr.get('form'),'dateFiled':fr.get('dateFiled'),'filename':fr.get('filename'),'transport':tr,'stateCode':st,'historicalEntityName':name})
      if st:
       rec.update({'classification':'US' if st in US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_INDEX_HEADERS_COMPANY_DATA_STATE','historicalEntityName':name,'evidenceForm':fr.get('form'),'evidenceDateFiled':fr.get('dateFiled'),'evidenceFilename':fr.get('filename'),'evidenceTransport':tr});break
     except Exception as e:
      errors+=1;rec['attempts'].append({'form':fr.get('form'),'dateFiled':fr.get('dateFiled'),'filename':fr.get('filename'),'error':type(e).__name__})
    if rec['classification']!='UNKNOWN':break
    time.sleep(.01)
  if rec['classification']!='UNKNOWN':resolved+=1;us+=rec['classification']=='US';nonus+=rec['classification']=='NON_US'
  results.append(rec)
  if (i+1)%50==0:print('PROGRESS',json.dumps({'shard':shard_i,'done':i+1,'resolved':resolved,'errors':errors}),flush=True)
 out={'purpose':'Return-independent PIT recovery of strict-country UNKNOWN identities using only official SEC accession index-headers pages. Classification requires historical cleaned exact issuer-form name -> exactly one CIK in pre-report-date SEC master index, then matching COMPANY DATA name+CIK+STATE OF INCORPORATION in the same historical accession header. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','shardIndex':shard_i,'shardCount':shard_n,'allInputUnknownCount':len(all_unknown),'shardInputUnknownCount':len(unknown),'historicalExactUniqueCikCount':sum(r['historicalExactCik'] is not None for r in results),'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'remainingUnknownCount':len(unknown)-resolved,'transportErrorCount':errors,'masterYears':years,'masterIndexTransports':transports,'results':results}
 out_path=ROOT/f'data/research/country-index-headers-recovery-v29-shard-{shard_i}.json';out_path.parent.mkdir(parents=True,exist_ok=True);out_path.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)
if __name__=='__main__':main()
