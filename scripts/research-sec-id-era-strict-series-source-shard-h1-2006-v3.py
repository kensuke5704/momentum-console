#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INV=ROOT/'data/research/sec-complete-portfolio-inventory-h1-2006.json'
PREF=ROOT/'data/research/sec-etf-registrant-operational-prefilter-h1-2006.json'
MANDATORY='2006-02-06'; ASOF='2006-06-30'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m

base=load('catalog_base',ROOT/'scripts/research-sec-historical-etf-series-source-catalog-h1-2006.py')
h2diag=load('h2diag',ROOT/'scripts/research-sec-complete-portfolio-title-diagnostic-h2-2005.py')
ETF_CLASS=re.compile(r'\b(?:ETF\s+SHARES?|VIPER(?:\s+SHARES?)?|EXCHANGE[- ]TRADED(?:\s+SHARES?)?)\b',re.I)
TITLE_ETF=re.compile(r'\b(?:ETF|SPDR|ISHARES|STREETTRACKS|VIPER)\b',re.I)
REGISTRANT_ETF=re.compile(r'\b(?:ETF|EXCHANGE[- ]TRADED)\b',re.I)

def prospectus_set(rows):
    chosen={}
    for r in rows:
        if r['form'] in base.CORE and r['dateFiled']<=ASOF:chosen[r['filename']]=r
    # Supplements are numerous; retain latest public supplement at each month-end.
    for year,months in ((2005,range(1,13)),(2006,range(1,7))):
        for month in months:
            import calendar
            day=calendar.monthrange(year,month)[1]
            asof=f'{year:04d}-{month:02d}-{day:02d}'
            if asof>ASOF:asof=ASOF
            avail=[r for r in rows if r['form'] in base.SUPP and r['dateFiled']<=asof]
            if avail:
                rr=max(avail,key=lambda x:(x['dateFiled'],x['form'],x['filename']));chosen[rr['filename']]=rr
    return sorted(chosen.values(),key=lambda r:(r['dateFiled'],r['form'],r['filename']))

def structural_binding(series,registrant,series_count):
    if any(ETF_CLASS.search(c.get('className') or '') for c in series.get('classes',[])):
        return 'EXPLICIT_ETF_CLASS_METADATA'
    if TITLE_ETF.search(series.get('seriesName') or ''):
        return 'SERIES_TITLE_EXPLICIT_ETF_SEMANTIC'
    if REGISTRANT_ETF.search(registrant or ''):
        return 'REGISTRANT_EXPLICIT_ETF_SEMANTIC'
    if series_count==1:
        return 'SINGLE_SERIES_FILING_WITH_ISSUER_OWN_EVIDENCE'
    return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--shard',type=int,required=True);ap.add_argument('--shards',type=int,default=4);args=ap.parse_args()
    inv=json.loads(INV.read_text());pref=json.loads(PREF.read_text());all_ciks=sorted(set(pref['positiveCiks']));assigned=[c for i,c in enumerate(all_ciks) if i%args.shards==args.shard];aset=set(assigned)
    pros,trs=base.load_prospectus(aset)
    ops=defaultdict(list);pros_audit=[]
    for cik in assigned:
        for f in prospectus_set(pros.get(cik,[])):
            rec={**f,'submissionUrl':base.su(f['filename'])}
            try:
                text,tr,_,prior=base.ft(rec['submissionUrl'],5_000_000,24);c=base.rule.find(base.rule.CREATION,text);e=base.rule.find(base.rule.EXCHANGE,text)
                rec.update({'transport':tr,'priorErrors':prior,'creationIssuerOwnEvidence':bool(c),'exchangeIssuerOwnEvidence':bool(e)})
                if c and e:ops[cik].append({'dateFiled':f['dateFiled'],'form':f['form'],'filename':f['filename']})
            except Exception as ex:rec.update({'error':type(ex).__name__,'errorDetail':str(ex)[:700]})
            pros_audit.append(rec)
    for cik in ops:ops[cik].sort(key=lambda x:(x['dateFiled'],x['filename']))

    occurrences=[];source_audit=[]
    rows=[r for r in inv['rows'] if r['cik'] in aset and MANDATORY<=r['dateFiled']<=ASOF]
    for row in rows:
        rec={k:row.get(k) for k in ('cik','company','form','dateFiled','filename','accession','indexUrl')}
        try:
            series,itr,iprior=base.parse_index_series(row['indexUrl']);submission,tr=h2diag.fetch(row['filename']);primary,desc,text,doctype=h2diag.primary_document(submission,row['form']);windows=h2diag.marker_windows(text)
            rec.update({'indexTransport':itr,'indexPriorErrors':iprior,'indexSeriesCount':len(series),'transport':tr,'primaryDocument':primary,'primaryDocumentType':doctype,'documentDescription':desc,'scheduleMarkerCount':len(windows),'hasCompletePortfolioSchedule':bool(windows)})
            accepted=[]
            if windows and ops.get(row['cik']):
                earliest_op=ops[row['cik']][0]
                for s in series:
                    binding=structural_binding(s,row['company'],len(series))
                    if not binding:continue
                    item={**row,'seriesId':s['seriesId'],'seriesName':s.get('seriesName') or '', 'classes':s.get('classes',[]),'binding':binding,'evidenceDateFiled':earliest_op['dateFiled'],'evidenceForm':earliest_op['form'],'evidenceFilename':earliest_op['filename']}
                    occurrences.append(item);accepted.append(s['seriesId'])
            rec['acceptedSeriesIds']=accepted
        except Exception as ex:rec.update({'error':type(ex).__name__,'errorDetail':str(ex)[:700]})
        source_audit.append(rec);print('SOURCE',json.dumps({k:rec.get(k) for k in ('cik','form','dateFiled','indexSeriesCount','scheduleMarkerCount','error')}),flush=True)
    # Earliest public Series metadata occurrence defines identity metadata; operational evidence may predate it.
    positives={}
    for r in sorted(occurrences,key=lambda x:(x['dateFiled'],x['seriesId'],x['accession'] or '')):
        if r['seriesId'] not in positives:
            positives[r['seriesId']]={'cik':r['cik'],'registrant':r['company'],'seriesId':r['seriesId'],'seriesName':r['seriesName'],'classes':r['classes'],'seriesMetadataFirstDate':r['dateFiled'],'evidenceDateFiled':r['evidenceDateFiled'],'evidenceForm':r['evidenceForm'],'evidenceFilename':r['evidenceFilename'],'binding':r['binding']}
    out={'purpose':'Production-independent post-2006-02-06 Series-ID ETF source shard with regime-aware evidence separation. Series ID/Class metadata comes only from post-mandatory complete-portfolio filing indexes. ETF operational evidence (issuer-own Creation Unit plus exchange listing/trading) may come from an earlier same-CIK prospectus that was already public. Series-level acceptance requires explicit ETF/VIPER class metadata, explicit ETF-semantic Series title or registrant legal name, or a single-Series filing. No trust-global local-title inheritance, later identity backfill, holdings outcomes, ranks, returns, or strategy results are used.','shard':args.shard,'shards':args.shards,'assignedRegistrantCount':len(assigned),'assignedCiks':assigned,'positiveSeriesCount':len(positives),'positiveSeries':sorted(positives.values(),key=lambda x:x['seriesId']),'sourceOccurrenceCount':len(occurrences),'sourceOccurrences':occurrences,'operationalEvidenceRegistrantCount':len(ops),'prospectusErrorCount':sum('error' in x for x in pros_audit),'sourceErrorCount':sum('error' in x for x in source_audit),'sourceNoScheduleCount':sum('error' not in x and not x.get('hasCompletePortfolioSchedule',False) for x in source_audit),'prospectusAudit':pros_audit,'sourceAudit':source_audit,'masterTransports':trs}
    path=ROOT/'data/research'/f'sec-id-era-strict-series-source-h1-2006-shard-{args.shard}.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('assignedCiks','positiveSeries','sourceOccurrences','prospectusAudit','sourceAudit','masterTransports')}),flush=True)
if __name__=='__main__':main()
