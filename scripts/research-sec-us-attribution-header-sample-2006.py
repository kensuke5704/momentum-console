#!/usr/bin/env python3
from __future__ import annotations
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAPPING=ROOT/'data/research/nq-npx-mapping-2006.json'
OUT=ROOT/'data/research/sec-us-attribution-header-sample-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
SAMPLE_N=24
ARCHIVE_CIK_RE=re.compile(r'/Archives/edgar/data/(\d+)/',re.I)
ARCHIVE_RE=re.compile(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"\'<>\)]+',re.I)
CANDIDATE_ROW_RE=re.compile(r'\|\s*\[(\d{10})\]\([^\)]*CIK=\1[^\)]*\)\s*\|\s*([^|]+?)\s*\|',re.I)
RAW_STATE_RE=re.compile(r'<STATE-OF-INCORPORATION>\s*([^\r\n<]+)',re.I)
RENDERED_STATE_RE=re.compile(r'State\s+of\s+Inc(?:orp)?\.?:\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?\b',re.I)
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}


def get(url,timeout=10):
    last=None
    for candidate in ('https://r.jina.ai/'+url,url):
        try:
            req=urllib.request.Request(candidate,headers=UA)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return r.read(2_000_000).decode('utf-8','replace'),candidate
        except Exception as e:last=repr(e)
    raise RuntimeError(last or 'fetch failed')


def sec_url(params):return 'https://www.sec.gov/cgi-bin/browse-edgar?'+urllib.parse.urlencode(params)

def clean_issuer(s):
    s=re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$','',s,flags=re.I)
    return ' '.join(s.replace('’',"'").split()).strip(' .,-')

def norm(s):
    s=clean_issuer(s).upper().replace('&',' AND ')
    s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b',' ',s)
    return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())

def variants(issuer):
    clean=clean_issuer(issuer); simple=' '.join(re.sub(r'[^A-Za-z0-9& ]+',' ',clean).split())
    no_suffix=' '.join(re.sub(r'\b(?:Incorporated|Inc|Corporation|Corp|Company|Co|Limited|Ltd|PLC|AG)\b\.?',' ',simple,flags=re.I).split())
    no_the=re.sub(r'^The\s+','',no_suffix,flags=re.I)
    out=[]
    for q in (clean,simple,no_suffix,no_the):
        q=q.strip(' .,-')
        if len(q)>=3 and q not in out:out.append(q)
    return out


def parse_browse(url):
    text,transport=get(url)
    urls=list(dict.fromkeys(ARCHIVE_RE.findall(text)))
    ciks=list(dict.fromkeys(m.group(1).zfill(10) for u in urls for m in [ARCHIVE_CIK_RE.search(u)] if m))
    candidates=[]
    for cik,raw in CANDIDATE_ROW_RE.findall(text):
        name=re.sub(r'\s+SIC:.*$','',raw.strip(),flags=re.I)
        candidates.append({'cik':cik,'name':name,'normalizedName':norm(name)})
    return {'transport':transport,'archiveUrls':urls[:20],'ciksFromArchive':ciks,'companyCandidates':candidates[:30]}

def browse_ticker(t,dateb):return parse_browse(sec_url({'action':'getcompany','CIK':t,'type':'','dateb':dateb.replace('-',''),'owner':'exclude','count':'40'}))

def browse_issuer(q,dateb):return parse_browse(sec_url({'action':'getcompany','company':q,'type':'','dateb':dateb.replace('-',''),'owner':'exclude','count':'40'}))

def browse_cik(cik,dateb):return parse_browse(sec_url({'action':'getcompany','CIK':cik,'type':'','dateb':dateb.replace('-',''),'owner':'exclude','count':'40'}))


def issuer_resolve(issuer,dateb):
    target=norm(issuer); direct={}; candidates={}; audits=[]
    for q in variants(issuer):
        try:
            b=browse_issuer(q,dateb); audits.append({'query':q,'archives':len(b['archiveUrls']),'ciks':b['ciksFromArchive'],'candidates':len(b['companyCandidates'])})
            if b['archiveUrls'] and len(b['ciksFromArchive'])==1:direct[b['ciksFromArchive'][0]]=b
            for c in b['companyCandidates']:candidates[c['cik']]=c
        except Exception as e:audits.append({'query':q,'error':type(e).__name__})
        time.sleep(.08)
    if len(direct)==1:
        cik,b=next(iter(direct.items()));return {'source':'ISSUER_VARIANT_DIRECT_SINGLE_PIT_CIK','cik':cik,'browse':b},audits
    exact=[c for c in candidates.values() if c['normalizedName']==target]
    pool=exact if exact else list(candidates.values())
    viable=[]
    for c in pool[:10]:
        try:
            b=browse_cik(c['cik'],dateb);audits.append({'candidateCik':c['cik'],'candidateName':c['name'],'archives':len(b['archiveUrls'])})
            if b['archiveUrls']:viable.append((c,b))
        except Exception as e:audits.append({'candidateCik':c['cik'],'error':type(e).__name__})
        time.sleep(.08)
    if len(viable)==1:
        c,b=viable[0];return {'source':'ISSUER_VARIANT_CANDIDATE_SINGLE_PIT_CIK','cik':c['cik'],'browse':b,'candidate':c},audits
    return None,audits


def complete_text_url(index_url):
    m=re.search(r'/(\d{10}-\d{2}-\d{6})-index\.htm$',index_url,re.I)
    if not m:return None
    acc=m.group(1)
    if acc.startswith('999999999') or acc.startswith('0000000000'):return None
    return index_url[:-10]+'.txt'  # replace -index.htm with .txt


def state_from_complete_submission(urls):
    errors=[]
    for idx in urls:
        txt=complete_text_url(idx)
        if not txt:continue
        try:
            text,transport=get(txt,12)
            vals=[x.strip().upper() for x in RAW_STATE_RE.findall(text)]+[x.strip().upper() for x in RENDERED_STATE_RE.findall(text)]
            vals=list(dict.fromkeys(vals))
            if vals:return vals[0],txt,transport,errors
        except Exception as e:errors.append(type(e).__name__)
        # Only a few issuer-filed submissions are needed; avoid rate-heavy scans.
        if len(errors)>=3:break
        time.sleep(.15)
    return None,None,None,errors


def resolve(row):
    out={**row}; ticker,issuer,dateb=row['ticker'],row['issuer'],row['asOfReportDate']
    try:
        b=browse_ticker(ticker,dateb);source='TICKER'
        if not b['archiveUrls']:
            r,audits=issuer_resolve(issuer,dateb);out['issuerAudits']=audits
            if r:
                source=r['source'];b=r['browse'];out['candidate']=r.get('candidate')
        out['archiveCount']=len(b['archiveUrls']);out['ciks']=b['ciksFromArchive']
        state,txt,transport,errors=state_from_complete_submission(b['archiveUrls'])
        if errors:out['transportErrors']=errors
        if txt:out['completeSubmissionUrl']=txt
        if state:
            out['stateCode']=state;out['classification']='US' if state in US_CODES else 'NON_US';out['resolutionSource']=source
        else:out['classification']='UNKNOWN'
    except Exception as e:out['classification']='UNKNOWN';out['error']=repr(e)
    return out


def main():
    mapping=json.loads(MAPPING.read_text());ids={}
    for d in mapping.get('details',[]):
        if d.get('status')!='MATCHED_UNIQUE' or len(d.get('identities',[]))!=1:continue
        i=d['identities'][0];key=(i['ticker'],i['securityId']);cand={'ticker':i['ticker'],'securityId':i['securityId'],'issuer':d['description'],'asOfReportDate':d['reportDate']}
        if key not in ids or cand['asOfReportDate']<ids[key]['asOfReportDate']:ids[key]=cand
    pop=sorted(ids.values(),key=lambda x:(x['ticker'],x['securityId'],x['issuer']))
    n=min(SAMPLE_N,len(pop));pos=sorted(set(min(len(pop)-1,(i*len(pop))//n) for i in range(n)));sample=[pop[i] for i in pos]
    print('SAMPLE',json.dumps({'uniqueIdentityPopulation':len(pop),'sampleN':len(sample),'positions':pos}),flush=True)
    results=[]
    for j,row in enumerate(sample,1):
        r=resolve(row);results.append(r);print(f'{j}/{len(sample)}',json.dumps(r),flush=True);time.sleep(.12)
    counts={k:sum(1 for r in results if r['classification']==k) for k in ('US','NON_US','UNKNOWN')}
    sources=('TICKER','ISSUER_VARIANT_DIRECT_SINGLE_PIT_CIK','ISSUER_VARIANT_CANDIDATE_SINGLE_PIT_CIK')
    out={'year':2006,'purpose':'Same frozen actual-security US attribution sample, replacing multi-index-page scanning with historical complete-submission SGML header extraction. No returns/universe ranks used.','populationRule':'Deduplicate EC-filtered MATCHED_UNIQUE by ticker+securityId; earliest report date per identity.','sampleRule':'Same 24 deterministic equal-quantile positions as prior runs.','hierarchy':'Ticker PIT SEC browse; deterministic issuer variants only if ticker has no PIT filing; candidate accepted only if one PIT CIK. For country, skip SEC-letter accessions and read STATE-OF-INCORPORATION from the earliest retrievable historical complete-submission text; UNKNOWN on failure.','uniqueIdentityPopulation':len(pop),'sampleCount':len(results),'classificationCounts':counts,'resolvedRate':(counts['US']+counts['NON_US'])/len(results),'resolutionSources':{s:sum(1 for r in results if r.get('resolutionSource')==s) for s in sources},'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)

if __name__=='__main__':main()
