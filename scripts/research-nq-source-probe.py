#!/usr/bin/env python3
import re, urllib.request

UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
TARGET='https://www.sec.gov/Archives/edgar/data/1090117/0000891804-06-000308.txt'
CUSIP_RE=re.compile(r'(?<![A-Z0-9])([0-9A-Z*@#]{9})(?![A-Z0-9])')
req=urllib.request.Request('https://r.jina.ai/'+TARGET,headers=UA)
with urllib.request.urlopen(req,timeout=180) as r:text=r.read(2_000_000).decode('utf-8','replace')
lines=text.splitlines(); up=[x.upper() for x in lines]
starts=[i for i,x in enumerate(up) if 'SCHEDULE OF INVESTMENTS' in x or 'PORTFOLIO HOLDINGS' in x]
print('bytes=',len(text.encode()),'lines=',len(lines),'starts=',starts[:10])
start=starts[0] if starts else 0
hits=[]
for i in range(start,len(lines)):
    cs=CUSIP_RE.findall(up[i])
    if cs:
        hits.append((i,cs,lines[i]))
print('cusip_lines_after_start=',len(hits))
for i,cs,line in hits[:35]:
    print(f'ROW {i} CUSIP={cs} :: {line[:500]}')
    for j in range(max(start,i-2),min(len(lines),i+3)):
        if j!=i: print(f'  CTX {j}: {lines[j][:500]}')
# Also print markdown table headers/separators around the holdings region.
print('TABLELIKE')
shown=0
for i in range(start,min(len(lines),start+1200)):
    line=lines[i]
    if '|' in line and (re.search(r'[-:]{3,}',line) or any(k in line.upper() for k in ('VALUE','SHARES','PRINCIPAL','DESCRIPTION','SECURITY'))):
        print(i,line[:600]); shown+=1
        if shown>=40: break
