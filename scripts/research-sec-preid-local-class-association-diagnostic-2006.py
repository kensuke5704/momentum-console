#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/research/sec-legacy-etf-series-source-preid-2006.json'
OUT=ROOT/'data/research/sec-preid-local-class-association-diagnostic-2006.json'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m
strict=load('legacy_h2',ROOT/'scripts/research-sec-legacy-etf-series-source-h2-2005.py')
base=strict.base; h2diag=strict.h2diag
CLASS=strict.EXPLICIT_ETF_CLASS_LINE

def line_text(text): return h2diag.line_text(text).splitlines()

def main():
    d=json.loads(CAT.read_text())
    ids=[x for x in d['positiveIdentities'] if x.get('binding')=='LOCAL_EXPLICIT_ETF_CLASS_WITHIN_6_LINES']
    by_file=defaultdict(list)
    for x in ids: by_file[x['evidenceFilename']].append(x)
    fetched={}; errors=[]
    for fn in sorted(by_file):
        try:
            text,tr,_,prior=base.ft(base.su(fn),5_000_000,24)
            fetched[fn]={'lines':line_text(text),'transport':tr,'priorErrors':prior}
        except Exception as e: errors.append({'filename':fn,'error':type(e).__name__,'detail':str(e)[:700]})
    rows=[]
    for x in ids:
        f=fetched.get(x['evidenceFilename']); rec={k:x.get(k) for k in ('cik','registrant','seriesName','normalizedSeriesName','evidenceDateFiled','evidenceForm','evidenceFilename','explicitEtfClassLineDistance')}
        if not f:
            rec['error']='EVIDENCE_FETCH_FAILED';rows.append(rec);continue
        lines=f['lines']; norms=[base.norm(z) for z in lines]; title=x['normalizedSeriesName']
        hits=[]
        for i in range(len(lines)):
            for w in (1,2,3):
                if i+w>len(lines):continue
                phrase=base.norm(' '.join(lines[i:i+w]))
                if phrase==title or phrase.startswith(title+' '):
                    suffix=phrase[len(title):].strip() if phrase.startswith(title) else ''
                    hits.append({'line':i,'width':w,'phrase':phrase,'suffix':suffix})
        markers=[i for i,z in enumerate(lines) if CLASS.search(z)]
        pairs=[]
        for h in hits:
            for m in markers:
                dist=m-h['line']
                if abs(dist)<=10:
                    lo=max(0,min(h['line'],m)-2);hi=min(len(lines),max(h['line']+h['width'],m+1)+3)
                    pairs.append({'titleLine':h['line'],'titleWidth':h['width'],'titlePhrase':h['phrase'],'titleSuffix':h['suffix'],'classLine':m,'signedDistance':dist,'absoluteDistance':abs(dist),'classText':lines[m],'context':[{'line':j,'text':lines[j]} for j in range(lo,hi)]})
        pairs.sort(key=lambda p:(p['absoluteDistance'],0 if p['signedDistance']>=0 else 1,p['titleLine'],p['classLine']))
        rec.update({'titleHitCount':len(hits),'classMarkerCount':len(markers),'nearPairCount':len(pairs),'nearestPairs':pairs[:8]})
        rows.append(rec)
    out={'purpose':'Diagnostic only. For every pre-Series-ID identity accepted solely by local explicit ETF/VIPER class proximity, preserve exact title-hit and class-marker direction/context. This artifact does not alter source selection.','localIdentityCount':len(ids),'evidenceFileCount':len(by_file),'fetchErrorCount':len(errors),'fetchErrors':errors,'rows':rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'localIdentityCount':len(ids),'evidenceFileCount':len(by_file),'fetchErrorCount':len(errors)},indent=2))
if __name__=='__main__':main()
