#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/research/sec-legacy-etf-series-source-preid-2006.json'
OUT=ROOT/'data/research/sec-preid-direct-class-association-diagnostic-2006.json'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m
strict=load('legacy_h2',ROOT/'scripts/research-sec-legacy-etf-series-source-h2-2005.py')
base=strict.base;h2diag=strict.h2diag
CLASS_TOKEN=re.compile(r'\b(?:VIPER(?:S)?|ETF|EXCHANGE[- ]TRADED)\b',re.I)
CLASS_ONLY=re.compile(r'^\s*(?:VIPER(?:S)?(?:\s+SHARES?)?|ETF\s+SHARES?|EXCHANGE[- ]TRADED\s+SHARES?)\s*[\*\(\)/®R.-]*\s*$',re.I)

def main():
    d=json.loads(CAT.read_text())
    ids=[x for x in d['positiveIdentities'] if x.get('binding')=='LOCAL_EXPLICIT_ETF_CLASS_WITHIN_6_LINES']
    by_file=defaultdict(list)
    for x in ids:by_file[x['evidenceFilename']].append(x)
    fetched={};errors=[]
    for fn in sorted(by_file):
        try:
            text,tr,_,prior=base.ft(base.su(fn),5_000_000,24)
            fetched[fn]={'lines':h2diag.line_text(text).splitlines(),'transport':tr,'priorErrors':prior}
        except Exception as e:errors.append({'filename':fn,'error':type(e).__name__,'detail':str(e)[:700]})
    rows=[]
    for x in ids:
        rec={k:x.get(k) for k in ('cik','registrant','seriesName','normalizedSeriesName','evidenceDateFiled','evidenceForm','evidenceFilename','explicitEtfClassLineDistance')}
        f=fetched.get(x['evidenceFilename'])
        if not f:rec['directAssociation']=False;rec['error']='EVIDENCE_FETCH_FAILED';rows.append(rec);continue
        lines=f['lines'];title=x['normalizedSeriesName'];assocs=[]
        for i in range(len(lines)):
            for width in (1,2,3):
                if i+width>len(lines):continue
                phrase=' '.join(lines[i:i+width]);norm=base.norm(phrase)
                pos=norm.find(title)
                if pos<0:continue
                # Same title phrase/line must itself carry an ETF/VIPER class token after the title.
                suffix=norm[pos+len(title):].strip()
                if suffix and CLASS_TOKEN.search(suffix):
                    assocs.append({'type':'TITLE_PHRASE_CARRIES_CLASS','line':i,'width':width,'phrase':phrase,'normalizedSuffix':suffix})
                # Or the next non-empty line immediately following an exact title phrase is a class-only line.
                if norm==title:
                    j=i+width
                    while j<len(lines) and not lines[j].strip():j+=1
                    if j<len(lines) and j<=i+width+1 and CLASS_ONLY.fullmatch(lines[j].strip()):
                        assocs.append({'type':'IMMEDIATE_CLASS_ONLY_LINE','line':i,'width':width,'titlePhrase':phrase,'classLine':j,'classText':lines[j]})
        # Deduplicate mechanically identical associations.
        uniq=[];seen=set()
        for a in assocs:
            k=json.dumps(a,sort_keys=True)
            if k not in seen:seen.add(k);uniq.append(a)
        rec['directAssociation']=bool(uniq);rec['directAssociationCount']=len(uniq);rec['associations']=uniq[:12]
        rows.append(rec)
    accepted=[r for r in rows if r['directAssociation']]
    rejected=[r for r in rows if not r['directAssociation']]
    out={'purpose':'Diagnostic only. Re-test pre-Series-ID identities previously accepted only by <=6-line ETF/VIPER proximity. Direct Series-level association requires the exact normalized Series title phrase itself to carry a trailing ETF/VIPER/Exchange-Traded class token, or an exact title phrase to be immediately followed by a class-only line. Generic nearby section prose is not sufficient. No later Series IDs, holdings, ranks, returns or strategy outcomes are used.','inputIdentityCount':len(ids),'directAcceptedCount':len(accepted),'directRejectedCount':len(rejected),'fetchErrorCount':len(errors),'fetchErrors':errors,'rows':rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('rows','fetchErrors')},indent=2))
if __name__=='__main__':main()
