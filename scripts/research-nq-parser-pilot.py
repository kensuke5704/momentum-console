#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, time, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IDX=ROOT/'data'/'research'/'nq-index-2006.json'
OUT=ROOT/'data'/'research'/'nq-parser-pilot-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain'}
CATEGORY_RE=re.compile(r'\s[-–—]\s*\(?\d+(?:\.\d+)?%|TOTAL INVESTMENTS|NET ASSETS|TOTAL LONG|TOTAL SHORT',re.I)
NUM_RE=re.compile(r'^\(?\$?\s*[-+]?\d[\d,]*(?:\.\d+)?\s*\)?$')
TAIL_RE=re.compile(r'^(.*?)(\d[\d,]*(?:\.\d+)?)\s+(?:([A-Z]{3})\s+)?\$?\s*(\d[\d,]*(?:\.\d+)?)\s*$')


def sec_url(filename:str)->str:return 'https://www.sec.gov/Archives/'+filename.lstrip('/')
def get_text(url:str)->str:
    req=urllib.request.Request('https://r.jina.ai/'+url,headers=UA)
    with urllib.request.urlopen(req,timeout=180) as r:return r.read(4_000_000).decode('utf-8','replace')

def sample_filings(filings):
    by=defaultdict(list)
    for x in filings:
        if x['form']=='N-Q':by[x['dateFiled'][:7]].append(x)
    out=[]
    for month in sorted(by):
        rows=by[month]; out.extend([rows[0]] if len(rows)==1 else [rows[len(rows)//3],rows[(2*len(rows))//3]])
    return out

def clean_cell(s:str)->str:
    s=re.sub(r'(?is)<BR\s*/?>',' ',s);s=re.sub(r'(?is)<[^>]+>',' ',s);s=html.unescape(s).replace('\xa0',' ');return ' '.join(s.split())
def html_rows(text:str):
    out=[]
    for m in re.finditer(r'(?is)<TR\b[^>]*>(.*?)</TR>',text):
        cells=[clean_cell(x) for x in re.findall(r'(?is)<TD\b[^>]*>(.*?)</TD>',m.group(1))]
        if cells and any(c for c in cells):out.append(cells)
    return out

def parse_number(s:str):
    s=s.strip().replace('$','').replace(',','').replace(' ','');neg=s.startswith('(') and s.endswith(')')
    if neg:s=s[1:-1]
    if not re.fullmatch(r'[-+]?\d+(?:\.\d+)?',s):return None
    try:v=float(s)
    except:return None
    return -v if neg else v

def is_value_cell(s:str)->bool:return bool(NUM_RE.match(s.strip())) and '%' not in s and '/' not in s
def text_candidates(cells):
    return [(j,c) for j,c in enumerate(cells) if c and c not in ('$','—','-') and re.search(r'[A-Za-z]{3}',c) and not re.fullmatch(r'[A-Za-z]{1,4}[+-]?\*{0,3}',c)]

def dedupe(hs):
    out=[];seen=set()
    for h in hs:
        key=(h['description'],h.get('quantityOrPrincipal'),h['marketValue'])
        if key not in seen:seen.add(key);out.append(h)
    return out

def parse_html_holdings(text:str):
    rows=html_rows(text);holdings=[];pending='';last=None;started=False
    for cells in rows:
        joined=' | '.join(cells);up=joined.upper()
        if any(k in up for k in ('PORTFOLIO OF INVESTMENTS','SCHEDULE OF INVESTMENTS','PORTFOLIO HOLDINGS')):started=True
        if not started:continue
        vals=[(j,parse_number(c)) for j,c in enumerate(cells) if is_value_cell(c)];texts=text_candidates(cells)
        if vals and texts:
            vj,value=vals[-1];descs=[(j,c) for j,c in texts if j<vj]
            if value is not None and value>0 and descs:
                dj,desc=max(descs,key=lambda z:len(z[1]))
                if CATEGORY_RE.search(desc) or desc.upper().startswith(('TOTAL','NET ASSET','PREFERRED SHARES')):pending='';continue
                quantity=next((v for j,v in vals if j<dj and v is not None and v>0),None)
                full=(' '.join(x for x in (pending,desc) if x)).strip()
                if len(full)>=8 and not any(k in full.upper() for k in ('OPTIONAL CALL','PRINCIPAL AMOUNT','MARKET VALUE')):
                    h={'description':full,'quantityOrPrincipal':quantity,'marketValue':value};holdings.append(h);last=h;pending='';continue
        descs=[c for _,c in texts]
        if descs:
            desc=max(descs,key=len)
            if CATEGORY_RE.search(desc):pending='';last=None;continue
            if len(desc)>=8 and not any(k in desc.upper() for k in ('PORTFOLIO OF INVESTMENTS','UNAUDITED','PRINCIPAL','MARKET VALUE','RATINGS','OPTIONAL CALL')):
                if last is not None and not vals:last['description']=(last['description']+' '+desc).strip()
                else:pending=(pending+' '+desc).strip() if pending else desc
    return rows,dedupe(holdings)

def plain_lines(text:str):
    s=re.sub(r'(?is)<BR\s*/?>','\n',text);s=re.sub(r'(?is)</(?:P|DIV|TR|TD|PRE|TABLE)>','\n',s);s=re.sub(r'(?is)<[^>]+>',' ',s);s=html.unescape(s).replace('\xa0',' ')
    return [' '.join(x.split()) for x in s.splitlines()]

def clean_desc(s:str):
    s=re.sub(r'^[\s*]+','',s);s=re.sub(r'^(?:\([a-z0-9,]+\))+','',s,flags=re.I);s=re.sub(r'\.{2,}\s*$','',s);return ' '.join(s.split())

def parse_plain_holdings(text:str):
    lines=plain_lines(text);holdings=[];pending='';started=False;ended=False
    for line in lines:
        if not line:continue
        up=line.upper()
        if any(k in up for k in ('STATEMENT OF INVESTMENTS','SCHEDULE OF INVESTMENTS')):started=True;continue
        if not started:continue
        if any(k in up for k in ('ITEM 2. CONTROLS','ITEM 2. OTHER INFORMATION','NOTES TO STATEMENT OF INVESTMENTS')):
            if len(holdings)>=5:ended=True
        if ended:break
        if re.fullmatch(r'[-_= .]+',line):continue
        if re.fullmatch(r'[\d,()$ .]+',line):continue # subtotal/total only
        m=TAIL_RE.match(line)
        if m:
            prefix,qty,currency,value=m.groups();desc=clean_desc(prefix)
            q=parse_number(qty);v=parse_number(value)
            if v is None or v<=0 or q is None or q<=0:continue
            # Require a security-like prefix; dot leaders are common but not mandatory.
            if not re.search(r'[A-Za-z]{2}',desc):continue
            # If the line starts with coupon/tranche terms, inherit the preceding issuer parent.
            child=bool(re.match(r'^(?:\(?[a-z](?:,[a-z])*\)?\s*)?(?:REG\s+S|FRN|SERIES|SECURED|ZERO|\d+(?:\.\d+)?%)',desc,re.I))
            full=(' '.join(x for x in ((pending if child else ''),desc) if x)).strip()
            if len(full)<6:continue
            holdings.append({'description':full,'quantityOrPrincipal':q,'marketValue':v,'currency':currency});continue
        # Parent issuer lines usually end with comma and are followed by one or more tranche rows.
        if '%' not in line and len(line)>=5 and len(line)<=220 and re.search(r'[A-Za-z]{3}',line) and line.rstrip().endswith(','):
            pending=clean_desc(line)
        elif re.search(r'\b(?:LONG TERM INVESTMENTS|SHORT TERM INVESTMENTS|COMMON STOCKS?|CORPORATE BONDS?|COUNTRY|TOTAL)\b',up):
            pending=''
    return lines,dedupe(holdings)

def parse_holdings(text:str):
    hrows,h=parse_html_holdings(text);plines,p=parse_plain_holdings(text)
    # Format choice is parser-yield based only; never based on investment performance.
    if len(p)>len(h):return 'plain',len(hrows),len(plines),p
    return 'html',len(hrows),len(plines),h

def main():
    idx=json.loads(IDX.read_text());samples=sample_filings(idx['filings']);print('sample filings=',len(samples),flush=True);results=[]
    for i,x in enumerate(samples,1):
        url=sec_url(x['filename'])
        try:
            text=get_text(url);method,hrows,plines,holdings=parse_holdings(text);total=sum(h['marketValue'] for h in holdings);with_qty=sum(h.get('quantityOrPrincipal') is not None for h in holdings)
            r={'month':x['dateFiled'][:7],'cik':x['cik'],'company':x['company'],'dateFiled':x['dateFiled'],'filename':x['filename'],'url':url,'bytes':len(text.encode()),'method':method,'htmlRows':hrows,'plainLines':plines,'parsedHoldings':len(holdings),'parsedMarketValueTotal':total,'withQuantityOrPrincipal':with_qty,'quantityCoverage':with_qty/len(holdings) if holdings else 0,'sampleHoldings':holdings[:10]}
            print(f"{i}/{len(samples)} {r['month']} {x['company'][:32]} method={method} holdings={len(holdings)} qcov={r['quantityCoverage']:.2f} value={total:.0f}",flush=True)
            for h0 in holdings[:2]:print('  ',h0['description'][:150],h0.get('quantityOrPrincipal'),h0['marketValue'],flush=True)
        except Exception as e:r={'month':x['dateFiled'][:7],'company':x['company'],'filename':x['filename'],'error':repr(e)};print(i,'FAIL',repr(e),flush=True)
        results.append(r);time.sleep(.15)
    ok=[r for r in results if 'error' not in r];counts=sorted(r['parsedHoldings'] for r in ok)
    def rate(pred):return sum(1 for r in ok if pred(r))/len(ok) if ok else None
    methods=defaultdict(int)
    for r in ok:methods[r['method']]+=1
    summary={'year':2006,'sampleRule':'Two deterministic N-Q filings per filing month (1/3 and 2/3 positions in master-index order). Parser grammar fixed independently of backtest performance.','sampleCount':len(samples),'fetchSuccess':len(ok),'fetchRate':len(ok)/len(samples) if samples else None,'methodCounts':dict(methods),'atLeast1HoldingRate':rate(lambda r:r['parsedHoldings']>=1),'atLeast10HoldingsRate':rate(lambda r:r['parsedHoldings']>=10),'atLeast20HoldingsRate':rate(lambda r:r['parsedHoldings']>=20),'medianParsedHoldings':counts[len(counts)//2] if counts else None,'meanQuantityCoverage':sum(r['quantityCoverage'] for r in ok)/len(ok) if ok else None,'positiveMarketValueRate':rate(lambda r:r['parsedMarketValueTotal']>0),'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
