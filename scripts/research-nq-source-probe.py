#!/usr/bin/env python3
import re, urllib.request

UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
TARGET='https://www.sec.gov/Archives/edgar/data/1090117/0000891804-06-000308.txt'
TOKEN_RE=re.compile(r'(?<![A-Z0-9])([0-9A-Z*@#]{9})(?![A-Z0-9])')

def cusips(s:str):
    # CUSIP is 9 chars; require at least one digit to exclude ordinary 9-letter words.
    return [x for x in TOKEN_RE.findall(s.upper()) if any(c.isdigit() for c in x)]

req=urllib.request.Request('https://r.jina.ai/'+TARGET,headers=UA)
with urllib.request.urlopen(req,timeout=180) as r:text=r.read(2_000_000).decode('utf-8','replace')
lines=text.splitlines(); up=[x.upper() for x in lines]
starts=[i for i,x in enumerate(up) if 'SCHEDULE OF INVESTMENTS' in x or 'PORTFOLIO OF INVESTMENTS' in x or 'PORTFOLIO HOLDINGS' in x]
print('bytes=',len(text.encode()),'lines=',len(lines),'starts=',starts[:10])
start=starts[-1] if starts else 0
hits=[]
for i in range(start,len(lines)):
    cs=cusips(lines[i])
    if cs:hits.append((i,cs,lines[i]))
print('strict_cusip_lines_after_start=',len(hits),'unique=',len({c for _,cs,_ in hits for c in cs}))
for i,cs,line in hits[:45]:
    print(f'ROW {i} CUSIP={cs} :: {line[:700]}')
    for j in range(max(start,i-3),min(len(lines),i+4)):
        if j!=i: print(f'  CTX {j}: {lines[j][:700]}')
