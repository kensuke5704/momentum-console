#!/usr/bin/env python3
from __future__ import annotations
import re, urllib.parse, urllib.request

PAGES=[
 'https://financialreports.eu/filings/new-germany-fund-inc/regulatory-filings/2006/9788464/',
 'https://financialreports.eu/filings/mexico-fund-inc/regulatory-filings/2006/9134794/',
 'https://financialreports.eu/filings/nuveen-missouri-quality-municipal-income-fund/regulatory-filings/2006/10013829/',
]
UA={'User-Agent':'Mozilla/5.0 momentum-console research','Accept':'text/html,application/xhtml+xml'}

def fetch(url,limit=5_000_000):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=120) as r:
        b=r.read(limit);return r.status,r.geturl(),r.headers,b

def main():
    for page in PAGES:
        print('\nPAGE',page,flush=True)
        try:
            status,final,h,b=fetch(page); text=b.decode('utf-8','replace')
            print('status',status,'final',final,'bytes',len(b),'ctype',h.get('content-type'),flush=True)
            zips=sorted(set(re.findall(r'https?://[^"\'<>\s]+\.zip(?:\?[^"\'<>\s]*)?|[^"\'<>\s=/]+\.zip',text,re.I)))
            hrefs=[]
            for m in re.finditer(r'(?:href|src)=["\']([^"\']+)["\']',text,re.I):
                u=m.group(1)
                if '.zip' in u.lower() or any(k in u.lower() for k in ('download','original','filing')): hrefs.append(u)
            print('zip_tokens',zips[:30],flush=True)
            print('candidate_hrefs',hrefs[:80],flush=True)
            for token in zips[:10]:
                if token.startswith('http'):url=token
                elif token.startswith('/'):url=urllib.parse.urljoin(page,token)
                else:
                    # Try token itself relative to current page and site root.
                    candidates=[urllib.parse.urljoin(page,token),urllib.parse.urljoin('https://financialreports.eu/',token)]
                    for url in candidates:
                        try:
                            s,f,hh,bb=fetch(url,2_000_000)
                            print('ZIPTRY',url,'=>',s,f,len(bb),hh.get('content-type'),bb[:4],flush=True)
                        except Exception as e:print('ZIPFAIL',url,repr(e),flush=True)
                    continue
                try:
                    s,f,hh,bb=fetch(url,2_000_000);print('ZIPTRY',url,'=>',s,f,len(bb),hh.get('content-type'),bb[:4],flush=True)
                except Exception as e:print('ZIPFAIL',url,repr(e),flush=True)
            # print snippets around original filing / zip
            for pat in ('Original Filing','.zip','SCHEDULE OF INVESTMENTS'):
                i=text.lower().find(pat.lower())
                if i>=0: print('SNIP',pat,repr(text[max(0,i-800):i+1800]),flush=True)
        except Exception as e: print('PAGEFAIL',repr(e),flush=True)

if __name__=='__main__':main()
