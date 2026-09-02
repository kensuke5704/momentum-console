#!/usr/bin/env python3
import html, re, urllib.request

UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
TARGET='https://www.sec.gov/Archives/edgar/data/1090117/0000891804-06-000308.txt'
req=urllib.request.Request('https://r.jina.ai/'+TARGET,headers=UA)
with urllib.request.urlopen(req,timeout=180) as r:text=r.read(2_000_000).decode('utf-8','replace')

def cell_text(s):
    s=re.sub(r'(?is)<BR\s*/?>',' ',s)
    s=re.sub(r'(?is)<[^>]+>',' ',s)
    s=html.unescape(s).replace('\xa0',' ')
    return ' '.join(s.split())

rows=[]
for m in re.finditer(r'(?is)<TR\b[^>]*>(.*?)</TR>',text):
    cells=[cell_text(x) for x in re.findall(r'(?is)<TD\b[^>]*>(.*?)</TD>',m.group(1))]
    if cells: rows.append(cells)
print('bytes=',len(text.encode()),'htmlRows=',len(rows))
# Locate portfolio table by characteristic headers.
start=0
for i,cells in enumerate(rows):
    joined=' | '.join(cells).upper()
    if ('PRINCIPAL' in joined or 'SHARES' in joined) and ('MARKET VALUE' in joined or 'VALUE' in joined):
        start=i; print('HEADER',i,cells); break
shown=0
for i,cells in enumerate(rows[start:start+400],start):
    joined=' | '.join(cells)
    numeric=sum(bool(re.search(r'\d',c)) for c in cells)
    if numeric>=2 and any(re.search(r'[A-Za-z]{3}',c) for c in cells):
        print('DATA',i,repr(cells))
        shown+=1
        if shown>=45:break
print('candidateRowsShown=',shown)
