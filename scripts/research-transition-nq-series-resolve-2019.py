#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-nq-series-resolve-2019.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
# Fixed transition series from Production 2020-02 and owner CIK continuity evidence.
TARGETS={
 '0001329377':['S000010977','S000017177','S000017178'],
 '0001364608':['S000033237','S000050385'],
 '0001552740':['S000044209','S000053942','S000053943','S000053944','S000053945','S000053946','S000053947','S000053948'],
 '0001467831':['S000047480','S000050191'],
 '0001408970':['S000031813','S000055090','S000059263','S000067382'],
}
# latest-first, mechanically discovered before holdings inspection
ACCESSIONS={
 '0001329377':['0001445546-18-005192','0001445546-18-002558','0001445546-17-005277','0001445546-17-002502'],
 '0001364608':['0001445546-19-001205','0001445546-18-003914','0001445546-18-001247'],
 '0001552740':['0001445546-19-001208','0001445546-19-001184','0001445546-18-005174','0001445546-18-003912','0001445546-18-003903'],
 '0001467831':['0000894189-19-005882','0001580642-19-001028','0000894189-19-001075','0000894189-18-004455','0000894189-18-001135'],
 '0001408970':['0001615774-18-012797','0001615774-18-004004','0001615774-17-006737'],
}
SID_RE=re.compile(r'<SERIES-ID>\s*([^<\r\n]+)',re.I)
DOC_RE=re.compile(r'(?:Document\s*\|\s*Type|Document\s+Type|<FILENAME>)',re.I)
FILENAME_RE=re.compile(r'(?:<FILENAME>|\]\()([^\s<\)]+\.(?:htm|html|txt))(?:<|\))?',re.I)
REPORT_RE=re.compile(r'(?:Period of Report|CONFORMED PERIOD OF REPORT[:\s]+)\s*(\d{4}[-/]?\d{2}[-/]?\d{2}|\d{8})',re.I)
FILING_RE=re.compile(r'(?:Filing Date|FILED AS OF DATE[:\s]+)\s*(\d{4}[-/]?\d{2}[-/]?\d{2}|\d{8})',re.I)

def get(url,timeout=20):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:raw=r.read(2_000_000)
   return raw.decode('utf-8','replace'),u,len(raw)
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')

def normdate(x):
 x=re.sub(r'\D','',x)
 return f'{x[:4]}-{x[4:6]}-{x[6:8]}' if len(x)>=8 else None

def index_url(cik,acc):
 return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}/{acc}-index.htm'

def parse_index(cik,acc):
 text,transport,n=get(index_url(cik,acc))
 sids=list(dict.fromkeys(x.strip() for x in SID_RE.findall(text)))
 # Prefer explicit N-Q document links from rendered index.
 files=[]
 for m in re.finditer(r'\[([^\]]+)\]\((https?://www\.sec\.gov/Archives/edgar/data/[^\)]+)\)',text,re.I):
  label,url=m.group(1),m.group(2)
  if re.search(r'cert',label,re.I):continue
  if re.search(r'\.(?:htm|html|txt)(?:$|\?)',url,re.I):files.append(url)
 if not files:
  for f in FILENAME_RE.findall(text):
   if 'cert' not in f.lower():files.append(f)
 report=REPORT_RE.search(text); filed=FILING_RE.search(text)
 return {'accession':acc,'indexUrl':index_url(cik,acc),'transport':transport,'bytes':n,'seriesIds':sids,'documentCandidates':list(dict.fromkeys(files))[:8],'reportDate':normdate(report.group(1)) if report else None,'filingDate':normdate(filed.group(1)) if filed else None,'snippet':' '.join(text.split())[:900]}

def main():
 resolved={};audits=[]
 for cik,targets in TARGETS.items():
  unresolved=set(targets)
  for acc in ACCESSIONS[cik]:
   try:info=parse_index(cik,acc)
   except Exception as e:
    info={'accession':acc,'error':repr(e),'seriesIds':[],'documentCandidates':[]}
   hits=sorted(unresolved & set(info.get('seriesIds',[])))
   info['targetHits']=hits;audits.append({'cik':cik,**info})
   print(cik,acc,'hits',hits,'sids',len(info.get('seriesIds',[])),'docs',info.get('documentCandidates',[])[:2],flush=True)
   for sid in hits:
    resolved[sid]={'cik':cik,**info}
    unresolved.discard(sid)
   if not unresolved:break
   time.sleep(.15)
 out={'purpose':'Resolve latest pre-2020 N-Q containing each fixed transition series using series metadata only; holdings and Universe outcomes are not used for selection.','targetSeries':sum(len(x) for x in TARGETS.values()),'resolvedSeries':len(resolved),'unresolvedSeries':sorted(set(sum(TARGETS.values(),[]))-set(resolved)),'resolved':resolved,'audits':audits}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('resolved','audits')}),flush=True)
if __name__=='__main__':main()
