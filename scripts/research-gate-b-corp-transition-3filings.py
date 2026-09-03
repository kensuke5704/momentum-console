#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from collections import Counter
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]/'data/research/gate-b-corp-transition-3filings.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,application/xml,*/*'}
FILINGS=[
 ('S000057700','1645194','000175272420012434','0001752724-20-012434'),
 ('S000063326','1479026','000175272420013847','0001752724-20-013847'),
 ('S000061208','1540305','000114554920003103','0001145549-20-003103'),
]

def get(url):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=60) as r:return r.read(8_000_000).decode('utf-8','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')

def val(block,names):
 for n in names:
  m=re.search(r'<(?:[^:>]+:)?'+n+r'[^>]*>\s*([^<]+?)\s*</',block,re.I)
  if m:return re.sub(r'\s+',' ',m.group(1)).strip().upper()
 return ''

def main():
 rows=[]
 for sid,cik,accdir,acc in FILINGS:
  url=f'https://www.sec.gov/Archives/edgar/data/{cik}/{accdir}/{acc}.txt'
  try:text,tr=get(url)
  except Exception as e:
   rows.append({'seriesId':sid,'accession':acc,'error':repr(e)});continue
  blocks=re.findall(r'<(?:[^:>]+:)?invstOrSec\b[^>]*>(.*?)</(?:[^:>]+:)?invstOrSec>',text,re.I|re.S)
  c=Counter(); examples={}
  tagSample=sorted(set(re.findall(r'<(?:[^:>]+:)?([A-Za-z][A-Za-z0-9_]*)\b',blocks[0] if blocks else '')))
  for b in blocks:
   asset=val(b,['assetCat','assetCategory']); country=val(b,['invCountry','investmentCountry','country']); issuer=val(b,['issuerCat','issuerType'])
   key=(asset,country,issuer);c[key]+=1
   if asset=='EC' and country=='US' and issuer!='CORP' and len(examples)<20:
    name=val(b,['name','issuerName']);examples.setdefault(issuer or 'MISSING',[]).append(name)
  ecus=sum(n for (a,co,i),n in c.items() if a=='EC' and co=='US')
  corp=sum(n for (a,co,i),n in c.items() if a=='EC' and co=='US' and i=='CORP')
  types=Counter()
  for (a,co,i),n in c.items():
   if a=='EC' and co=='US':types[i or 'MISSING']+=n
  rows.append({'seriesId':sid,'accession':acc,'transport':tr,'investmentBlocks':len(blocks),'ecUs':ecus,'ecUsCorp':corp,'corpShareWithinEcUs':corp/ecus if ecus else None,'issuerTypesWithinEcUs':dict(types),'nonCorpExamples':examples,'firstBlockTagNames':tagSample})
  print('ROW',json.dumps(rows[-1]),flush=True)
 out={'purpose':'Direct raw-filing transition diagnostic: among holdings with ASSET_CAT=EC and INVESTMENT_COUNTRY=US, measure whether ISSUER_TYPE=CORP removes material holdings in the exact three first Production source filings. XML issuer category is read from issuerCat (with issuerType fallback). No strategy returns or Universe ranking used.','rows':rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
