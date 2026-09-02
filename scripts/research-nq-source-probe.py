#!/usr/bin/env python3
import html, re, urllib.request
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
TARGET='https://www.sec.gov/Archives/edgar/data/1090117/0000891804-06-000308.txt'
req=urllib.request.Request('https://r.jina.ai/'+TARGET,headers=UA)
with urllib.request.urlopen(req,timeout=180) as r:text=r.read(2_000_000).decode('utf-8','replace')
def clean(s):
    s=re.sub(r'(?is)<BR\s*/?>',' ',s); s=re.sub(r'(?is)<[^>]+>',' ',s); s=html.unescape(s).replace('\xa0',' '); return ' '.join(s.split())
rows=[]
for m in re.finditer(r'(?is)<TR\b[^>]*>(.*?)</TR>',text):
    cells=[clean(x) for x in re.findall(r'(?is)<TD\b[^>]*>(.*?)</TD>',m.group(1))]
    if cells and any(c for c in cells): rows.append(cells)
print('nonemptyRows=',len(rows))
for i,c in enumerate(rows):
    joined=' | '.join(c).upper()
    if any(k in joined for k in ('PORTFOLIO OF INVESTMENTS','PRINCIPAL','MARKET VALUE','EDUCATION AND CIVIC','CALIFORNIA EDUCATIONAL')):
        print('ANCHOR',i,repr(c))
print('FIRST180')
for i,c in enumerate(rows[:180]): print(i,repr(c))
