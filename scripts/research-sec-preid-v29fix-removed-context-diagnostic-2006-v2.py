#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/research/sec-legacy-etf-series-source-preid-direct-old-2006.json'
OUT=ROOT/'data/research/sec-preid-v29fix-removed-context-diagnostic-2006-v2.json'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m
preid=load('preid_direct_base',ROOT/'scripts/research-sec-legacy-etf-series-source-preid-shard-2006.py')
strict=preid.strict
base=preid.base
h2diag=preid.h2diag
CLASS_TOKEN=re.compile(r'\b(?:VIPER(?:S)?|ETF|EXCHANGE[- ]TRADED)\b',re.I)
CLASS_ONLY=re.compile(r'^(?:VIPER(?:S)?(?: SHARES?)?|ETF SHARES?|EXCHANGE[- ]TRADED SHARES?)\s*[\*\(\)/®R.-]*$',re.I)
TARGETS={
 ('0000036405','VANGUARD SMALL CAP GROWTH INDEX FUND'),
 ('0000036405','VANGUARD SMALL CAP VALUE INDEX FUND'),
 ('0000036405','VANGUARD VALUE INDEX FUND'),
 ('0000052848','INTERNATIONAL GROWTH FUND'),
 ('0000857489','VANGUARD EMERGING MARKETS STOCK INDEX FUND'),
}

def main():
    d=json.loads(CAT.read_text())
    ids=[x for x in d['positiveIdentities'] if (x.get('cik'),x.get('normalizedSeriesName')) in TARGETS]
    rows=[];cache={}
    for x in ids:
        fn=x['evidenceFilename']
        if fn not in cache:
            text,tr,_,prior=base.ft(base.su(fn),5_000_000,24)
            cache[fn]={'lines':h2diag.line_text(text).splitlines(),'transport':tr,'priorErrors':prior}
        lines=cache[fn]['lines'];title=x['normalizedSeriesName'];hits=[]
        for i in range(len(lines)):
            for width in (1,2,3):
                if i+width>len(lines):continue
                phrase=' '.join(lines[i:i+width]);n=base.norm(phrase);pos=n.find(title)
                if pos<0:continue
                suffix=n[pos+len(title):].strip();nxt=i+width
                hits.append({
                  'line':i,'width':width,'phrase':phrase,'normalizedPhrase':n,
                  'suffix':suffix,'acceptedTitlePhrase':preid.accepted_title_phrase(n,title),
                  'suffixHasClassToken':bool(suffix and CLASS_TOKEN.search(suffix)),
                  'nextLine':lines[nxt] if nxt<len(lines) else None,
                  'nextLineClassOnly':bool(nxt<len(lines) and CLASS_ONLY.fullmatch(base.norm(lines[nxt]).strip())),
                  'contextBefore':lines[max(0,i-3):i],
                  'contextAfter':lines[i+width:min(len(lines),i+width+4)],
                })
        rows.append({'cik':x['cik'],'seriesName':x['seriesName'],'normalizedSeriesName':title,'evidenceFilename':fn,'evidenceDateFiled':x['evidenceDateFiled'],'evidenceForm':x['evidenceForm'],'oldExplicitEtfClassLineDistance':x.get('explicitEtfClassLineDistance'),'hits':hits[:40]})
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'rows':rows},indent=2)+'\n')
    print(json.dumps([{'cik':r['cik'],'seriesName':r['seriesName'],'hitCount':len(r['hits'])} for r in rows],indent=2))
if __name__=='__main__':main()
