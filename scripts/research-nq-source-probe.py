#!/usr/bin/env python3
import html,re,urllib.request
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,*/*'}
TARGET='https://www.sec.gov/Archives/edgar/data/909112/0000909112-06-000003.txt'
req=urllib.request.Request('https://r.jina.ai/'+TARGET,headers=UA)
with urllib.request.urlopen(req,timeout=180) as r:text=r.read(2_000_000).decode('utf-8','replace')
print('bytes=',len(text.encode()),'TR=',len(re.findall(r'(?i)<TR\\b',text)),'PRE=',len(re.findall(r'(?i)<PRE\\b',text)))
# Strip tags while preserving line boundaries and inspect around portfolio/schedule markers.
s=re.sub(r'(?is)<BR\\s*/?>','\n',text); s=re.sub(r'(?is)</(?:P|DIV|TR|TD|PRE|TABLE)>','\n',s); s=re.sub(r'(?is)<[^>]+>',' ',s); s=html.unescape(s).replace('\xa0',' ')
lines=[' '.join(x.split()) for x in s.splitlines()]
marks=[i for i,x in enumerate(lines) if any(k in x.upper() for k in ('SCHEDULE OF INVESTMENTS','PORTFOLIO OF INVESTMENTS','PORTFOLIO HOLDINGS'))]
print('lines=',len(lines),'markers=',marks[:20])
for m in marks[:3]:
 print('--- MARK',m,'---')
 for i in range(max(0,m-10),min(len(lines),m+160)):
  if lines[i]: print(i,repr(lines[i][:900]))
# Also surface lines likely to be securities: letters plus >=2 numeric groups.
print('LIKELY')
shown=0
for i,x in enumerate(lines):
 if not x:continue
 nums=re.findall(r'(?<![A-Za-z])\\(?\\$?\\d[\\d,]*(?:\\.\\d+)?\\)?%?',x)
 if len(nums)>=2 and re.search(r'[A-Za-z]{4}',x):
  print(i,repr(x[:1000]));shown+=1
  if shown>=50:break
