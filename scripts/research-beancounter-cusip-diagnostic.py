#!/usr/bin/env python3
from __future__ import annotations
import gzip, json, re, urllib.request

SHARDS=[145,150,155,160]
BASE='https://huggingface.co/datasets/bradfordlevy/BeanCounter/resolve/main/train'
TARGET={'N-Q','N-Q/A'}
CONTIG=re.compile(r'(?<![A-Z0-9])([0-9A-Z*@#]{9})(?![A-Z0-9])')
SPLIT=re.compile(r'(?<![A-Z0-9])([0-9A-Z*@#]{6})[\s\-_/]*([0-9A-Z*@#]{2})[\s\-_/]*([0-9A-Z*@#])(?![A-Z0-9])')
EIGHT=re.compile(r'(?<![A-Z0-9])([0-9A-Z*@#]{8})(?![A-Z0-9])')

def val(c):
    if c.isdigit():return int(c)
    if 'A'<=c<='Z':return ord(c)-55
    return {'*':36,'@':37,'#':38}.get(c,-99)
def valid(s):
    if len(s)!=9:return False
    vs=[val(c) for c in s]
    if min(vs)<0:return False
    sm=0
    for i,v in enumerate(vs[:8]):
        x=v*(2 if i%2 else 1);sm+=x//10+x%10
    return (10-sm%10)%10==vs[8]

def check_for_8(s):
    vs=[val(c) for c in s]
    if len(vs)!=8 or min(vs)<0:return None
    sm=0
    for i,v in enumerate(vs):
        x=v*(2 if i%2 else 1);sm+=x//10+x%10
    return str((10-sm%10)%10)

def main():
    found=0
    for sh in SHARDS:
        url=f'{BASE}/bc-{sh:03d}-of-512.jsonl.gz'
        req=urllib.request.Request(url,headers={'User-Agent':'momentum-console research'})
        with urllib.request.urlopen(req,timeout=600) as raw, gzip.GzipFile(fileobj=raw) as gz:
            for line in gz:
                try:o=json.loads(line)
                except:continue
                if not str(o.get('date','')).startswith('2006-') or str(o.get('type_filing','')).upper() not in TARGET:continue
                text=str(o.get('text') or '');up=text.upper()
                if 'PORTFOLIO' not in up and 'SCHEDULE OF INVESTMENTS' not in up:continue
                cont=CONTIG.findall(up)
                split=[''.join(x) for x in SPLIT.findall(up)]
                eights=EIGHT.findall(up)
                vc=[x for x in cont if valid(x)];vs=[x for x in split if valid(x)]
                print('\nFILING',o.get('accession'),o.get('date'),'shard',sh,'text',len(text),'contig',len(set(cont)),'validContig',len(set(vc)),'split',len(set(split)),'validSplit',len(set(vs)),'eight',len(set(eights)),flush=True)
                # print lines that look like holdings / identifiers without dumping whole filing
                lines=text.splitlines();shown=0
                for i,l in enumerate(lines):
                    u=l.upper()
                    if CONTIG.search(u) or SPLIT.search(u) or ('CUSIP' in u):
                        print('CTX',repr(' | '.join(lines[max(0,i-1):min(len(lines),i+2)])[:900]),flush=True);shown+=1
                        if shown>=12:break
                if not shown:
                    for i,l in enumerate(lines):
                        if any(k in l.upper() for k in ('SCHEDULE OF INVESTMENTS','PORTFOLIO OF INVESTMENTS','PORTFOLIO')):
                            print('MARKER',repr(' | '.join(lines[i:min(len(lines),i+8)])[:1400]),flush=True);break
                print('SAMPLE_CONTIG',sorted(set(cont))[:30],flush=True)
                print('SAMPLE_SPLIT',sorted(set(split))[:30],flush=True)
                print('SAMPLE_EIGHT',[(x,check_for_8(x)) for x in sorted(set(eights))[:30]],flush=True)
                found+=1
                if found>=8:return

if __name__=='__main__':main()
