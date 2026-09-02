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

def sec_url(filename:str)->str:
    return 'https://www.sec.gov/Archives/'+filename.lstrip('/')

def get_text(url:str)->str:
    req=urllib.request.Request('https://r.jina.ai/'+url,headers=UA)
    with urllib.request.urlopen(req,timeout=180) as r:return r.read(4_000_000).decode('utf-8','replace')

def sample_filings(filings):
    by=defaultdict(list)
    for x in filings:
        if x['form']!='N-Q':continue
        by[x['dateFiled'][:7]].append(x)
    out=[]
    for month in sorted(by):
        rows=by[month]
        picks=[rows[0]] if len(rows)==1 else [rows[len(rows)//3],rows[(2*len(rows))//3]]
        out.extend(picks)
    return out

def clean_cell(s:str)->str:
    s=re.sub(r'(?is)<BR\s*/?>',' ',s)
    s=re.sub(r'(?is)<[^>]+>',' ',s)
    s=html.unescape(s).replace('\xa0',' ')
    return ' '.join(s.split())

def html_rows(text:str):
    out=[]
    for m in re.finditer(r'(?is)<TR\b[^>]*>(.*?)</TR>',text):
        cells=[clean_cell(x) for x in re.findall(r'(?is)<TD\b[^>]*>(.*?)</TD>',m.group(1))]
        if cells and any(c for c in cells):out.append(cells)
    return out

def parse_number(s:str):
    s=s.strip().replace('$','').replace(',','').replace(' ','')
    neg=s.startswith('(') and s.endswith(')')
    if neg:s=s[1:-1]
    if not re.fullmatch(r'[-+]?\d+(?:\.\d+)?',s):return None
    try:v=float(s)
    except:return None
    return -v if neg else v

def is_value_cell(s:str)->bool:
    if not NUM_RE.match(s.strip()):return False
    # Reject dates, percentages and obvious ratings/call fields.
    return '%' not in s and '/' not in s

def text_candidates(cells):
    out=[]
    for j,c in enumerate(cells):
        if not c or c in ('$','—','-'):continue
        if re.search(r'[A-Za-z]{3}',c) and not re.fullmatch(r'[A-Za-z]{1,4}[+-]?\*{0,3}',c):out.append((j,c))
    return out

def parse_holdings(text:str):
    rows=html_rows(text)
    holdings=[]; pending=''; last=None
    started=False
    for cells in rows:
        joined=' | '.join(cells)
        up=joined.upper()
        if any(k in up for k in ('PORTFOLIO OF INVESTMENTS','SCHEDULE OF INVESTMENTS','PORTFOLIO HOLDINGS')):started=True
        if not started:continue
        vals=[(j,parse_number(c)) for j,c in enumerate(cells) if is_value_cell(c)]
        texts=text_candidates(cells)
        # Data row: use right-most positive numeric as market value and a descriptive text cell before it.
        if vals and texts:
            vj,value=vals[-1]
            descs=[(j,c) for j,c in texts if j<vj]
            if value is not None and value>0 and descs:
                dj,desc=max(descs,key=lambda z:len(z[1]))
                # Ignore headers/totals and derivative/counterparty summary tables after the investment schedule.
                if CATEGORY_RE.search(desc) or desc.upper().startswith(('TOTAL','NET ASSET','PREFERRED SHARES')):
                    pending=''; continue
                quantity=None
                for j,v in vals:
                    if j<dj and v is not None and v>0:
                        quantity=v; break
                full=(' '.join(x for x in (pending,desc) if x)).strip()
                # A useful security description must contain letters and not be a generic column/header phrase.
                if len(full)>=8 and not any(k in full.upper() for k in ('OPTIONAL CALL','PRINCIPAL AMOUNT','MARKET VALUE')):
                    h={'description':full,'quantityOrPrincipal':quantity,'marketValue':value,'cells':cells}
                    holdings.append(h); last=h; pending=''; continue
        # Text-only row can either continue the previous security or provide a parent description for following tranches.
        descs=[c for _,c in texts]
        if descs:
            desc=max(descs,key=len)
            if CATEGORY_RE.search(desc):
                pending=''; last=None; continue
            if len(desc)>=8 and not any(k in desc.upper() for k in ('PORTFOLIO OF INVESTMENTS','UNAUDITED','PRINCIPAL','MARKET VALUE','RATINGS','OPTIONAL CALL')):
                if last is not None and not vals:
                    # Continuation immediately after a data row, common in bond schedules.
                    last['description']=(last['description']+' '+desc).strip()
                else:
                    pending=(pending+' '+desc).strip() if pending else desc
    # Deduplicate obvious repeated rows by description/value/quantity within one filing.
    uniq=[]; seen=set()
    for h in holdings:
        key=(h['description'],h['quantityOrPrincipal'],h['marketValue'])
        if key in seen:continue
        seen.add(key); uniq.append(h)
    return rows,uniq

def main():
    idx=json.loads(IDX.read_text()); samples=sample_filings(idx['filings'])
    print('sample filings=',len(samples),flush=True)
    results=[]
    for i,x in enumerate(samples,1):
        url=sec_url(x['filename'])
        try:
            text=get_text(url); rows,holdings=parse_holdings(text)
            total=sum(h['marketValue'] for h in holdings if h['marketValue']>0)
            with_qty=sum(h['quantityOrPrincipal'] is not None for h in holdings)
            r={'month':x['dateFiled'][:7],'cik':x['cik'],'company':x['company'],'dateFiled':x['dateFiled'],'filename':x['filename'],'url':url,'bytes':len(text.encode()),'htmlRows':len(rows),'parsedHoldings':len(holdings),'parsedMarketValueTotal':total,'withQuantityOrPrincipal':with_qty,'quantityCoverage':with_qty/len(holdings) if holdings else 0,'sampleHoldings':holdings[:10]}
            print(f"{i}/{len(samples)} {r['month']} {x['company'][:34]} rows={len(rows)} holdings={len(holdings)} qcov={r['quantityCoverage']:.2f} value={total:.0f}",flush=True)
            for h in holdings[:2]:print('  ',h['description'][:150],h['quantityOrPrincipal'],h['marketValue'],flush=True)
        except Exception as e:
            r={'month':x['dateFiled'][:7],'cik':x['cik'],'company':x['company'],'dateFiled':x['dateFiled'],'filename':x['filename'],'url':url,'error':repr(e)}
            print(i,'FAIL',repr(e),flush=True)
        results.append(r); time.sleep(0.15)
    ok=[r for r in results if 'error' not in r]
    counts=sorted(r['parsedHoldings'] for r in ok)
    def rate(pred):return sum(1 for r in ok if pred(r))/len(ok) if ok else None
    summary={'year':2006,'sampleRule':'Two deterministic N-Q filings per filing month (1/3 and 2/3 positions in master-index order). Parser fixed independently of backtest performance.','sampleCount':len(samples),'fetchSuccess':len(ok),'fetchRate':len(ok)/len(samples) if samples else None,'atLeast1HoldingRate':rate(lambda r:r['parsedHoldings']>=1),'atLeast10HoldingsRate':rate(lambda r:r['parsedHoldings']>=10),'atLeast20HoldingsRate':rate(lambda r:r['parsedHoldings']>=20),'medianParsedHoldings':counts[len(counts)//2] if counts else None,'meanQuantityCoverage':sum(r['quantityCoverage'] for r in ok)/len(ok) if ok else None,'positiveMarketValueRate':rate(lambda r:r['parsedMarketValueTotal']>0),'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)

if __name__=='__main__':main()
