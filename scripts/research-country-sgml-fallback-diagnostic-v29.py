#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'data/research'
SRC=R/'nq-hybrid-country-resolved-h1-2006.json'
OUT=R/'country-sgml-fallback-diagnostic-v29.json'

spec=importlib.util.spec_from_file_location('strict',ROOT/'scripts/research-nq-hybrid-country-strict-v5-h1-2006.py')
strict=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(strict)


def main():
    data=json.loads(SRC.read_text())
    candidates=[];seen=set()
    for row in data.get('resolutionAudit',[]):
        if row.get('classification')!='UNKNOWN':continue
        for attempt in row.get('attempts') or []:
            if attempt.get('historicalExactCikCount')!=1 or not attempt.get('seedCik'):continue
            form=attempt.get('issuerForm');cik=attempt.get('seedCik')
            for fa in attempt.get('filingAttempts') or []:
                url=fa.get('submissionUrl')
                if not url or fa.get('httpStatus')!=200:continue
                key=(form,cik,url)
                if key in seen:continue
                seen.add(key);candidates.append((row,attempt,fa))
                break
            break
        if len(candidates)>=120:break
    results=[]
    for row,attempt,fa in candidates:
        form=attempt['issuerForm'];cik=attempt['seedCik'];url=fa['submissionUrl']
        try:
            req=urllib.request.Request(url,headers=strict.flat.base.UA)
            with urllib.request.urlopen(req,timeout=20) as resp:
                text=resp.read(131072).decode('latin-1','replace')
            flat_state,flat_name=strict.flat.flat_submission_state(form,cik,text)
            sgml_state,sgml_name=strict.flat.base.sgml_entity_state(form,cik,text)
            results.append({'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'issuerForm':form,'seedCik':cik,'url':url,'flatState':flat_state,'sgmlState':sgml_state,'sgmlHistoricalName':sgml_name})
        except Exception as e:
            results.append({'ticker':row.get('ticker'),'securityId':row.get('securityId'),'issuerForm':form,'seedCik':cik,'url':url,'error':type(e).__name__})
    out={'sampleCount':len(results),'sgmlResolvedCount':sum(bool(x.get('sgmlState')) for x in results),'flatResolvedCount':sum(bool(x.get('flatState')) for x in results),'sgmlOnlyResolvedCount':sum(bool(x.get('sgmlState')) and not x.get('flatState') for x in results),'results':results}
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SGML_FALLBACK_DIAGNOSTIC',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
    for x in results:
        if x.get('sgmlState') and not x.get('flatState'):print('SGML_ONLY',json.dumps(x),flush=True)

if __name__=='__main__':main()
