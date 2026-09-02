#!/usr/bin/env python3
from __future__ import annotations
import gzip, json, os, re, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHARD=int(os.environ.get('BC_SHARD','143'))
BASE='https://huggingface.co/datasets/bradfordlevy/BeanCounter/resolve/main/train'
PATH=f'bc-{SHARD:03d}-of-512.jsonl.gz'
URL=f'{BASE}/{PATH}'
OUT=ROOT/'data'/'research'/f'beancounter-2006-shard-{SHARD:03d}.json'
TARGET={'N-Q','N-Q/A','N-CSR','N-CSR/A','N-CSRS','N-CSRS/A'}
CUSIP_RE=re.compile(r'(?<![A-Z0-9])([0-9A-Z*@#]{9})(?![A-Z0-9])')

def cusip_value(ch:str)->int:
    if ch.isdigit(): return int(ch)
    if 'A'<=ch<='Z': return ord(ch)-ord('A')+10
    return {'*':36,'@':37,'#':38}.get(ch,-999)

def valid_cusip(s:str)->bool:
    if len(s)!=9:return False
    vals=[cusip_value(c) for c in s]
    if any(v<0 for v in vals):return False
    total=0
    for i,v in enumerate(vals[:8]):
        x=v*(2 if i%2 else 1)
        total += x//10 + x%10
    return (10-total%10)%10 == vals[8]

def main():
    req=urllib.request.Request(URL,headers={'User-Agent':'momentum-console research','Accept':'application/gzip'})
    filings={}
    rows=0; target_rows=0; bytes_text=0
    min_date=None; max_date=None
    with urllib.request.urlopen(req,timeout=600) as raw:
        with gzip.GzipFile(fileobj=raw) as gz:
            for bline in gz:
                rows+=1
                if b'"type_filing"' not in bline: continue
                try:o=json.loads(bline)
                except Exception:continue
                d=str(o.get('date') or '')
                if min_date is None or d<min_date:min_date=d
                if max_date is None or d>max_date:max_date=d
                if not d.startswith('2006-'):continue
                form=str(o.get('type_filing') or '').upper()
                if form not in TARGET:continue
                target_rows+=1
                acc=str(o.get('accession') or '')
                if not acc:continue
                f=filings.get(acc)
                if f is None:
                    f={'accession':acc,'cik':acc.split('-')[0].lstrip('0') or '0','date':d,'tsAccept':o.get('ts_accept'),'form':form,'attachments':0,'portfolioMarker':False,'scheduleMarker':False,'cusips':set()}
                    filings[acc]=f
                f['attachments']+=1
                text=str(o.get('text') or '')
                bytes_text+=len(text.encode('utf-8','ignore'))
                up=text.upper()
                if 'PORTFOLIO' in up:f['portfolioMarker']=True
                if 'SCHEDULE OF INVESTMENTS' in up:f['scheduleMarker']=True
                for c in CUSIP_RE.findall(up):
                    if valid_cusip(c):f['cusips'].add(c)
                if rows%50000==0:print(f'shard={SHARD} rows={rows:,} filings={len(filings):,}',flush=True)
    result=[]
    for f in filings.values():
        result.append({**{k:v for k,v in f.items() if k!='cusips'},'cusipCount':len(f['cusips']),'cusips':sorted(f['cusips'])})
    result.sort(key=lambda x:(x['date'],x['accession']))
    form_counts=defaultdict(int)
    for f in result:form_counts[f['form']]+=1
    summary={'source':'bradfordlevy/BeanCounter','shard':SHARD,'path':PATH,'observedDateRange':[min_date,max_date],'rows':rows,'targetAttachmentRows':target_rows,'uniqueTargetFilings':len(result),'formCounts':dict(form_counts),'withPortfolioMarker':sum(bool(x['portfolioMarker']) for x in result),'withScheduleMarker':sum(bool(x['scheduleMarker']) for x in result),'withAnyValidCusip':sum(x['cusipCount']>0 for x in result),'withAtLeast10ValidCusips':sum(x['cusipCount']>=10 for x in result),'targetTextBytes':bytes_text,'filings':result}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,separators=(',',':'))+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='filings'}),flush=True)

if __name__=='__main__':main()
