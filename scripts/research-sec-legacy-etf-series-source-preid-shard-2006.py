#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import defaultdict, Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
H2=ROOT/'data/research/sec-complete-portfolio-inventory-h2-2005.json'
H1=ROOT/'data/research/sec-complete-portfolio-inventory-h1-2006.json'
PREF=ROOT/'data/research/sec-etf-registrant-operational-prefilter-h1-2006.json'
SERIES_ID_START='2006-02-06'; SOURCE_CUTOFF='2006-02-05'; EVIDENCE_CUTOFF='2006-02-28'
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28')]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(m);return m

strict=load('legacy_h2',ROOT/'scripts/research-sec-legacy-etf-series-source-h2-2005.py')
base=strict.base; h2diag=strict.h2diag

def prospectus_set(rows):
    chosen={}
    for r in rows:
        if r['form'] in base.CORE and r['dateFiled']<=EVIDENCE_CUTOFF: chosen[r['filename']]=r
    for asof in ('2005-07-31','2005-08-31','2005-09-30','2005-10-31','2005-11-30','2005-12-30','2006-01-31','2006-02-28'):
        avail=[r for r in rows if r['form'] in base.SUPP and r['dateFiled']<=asof]
        if avail:
            r=max(avail,key=lambda x:(x['dateFiled'],x['form'],x['filename']));chosen[r['filename']]=r
    return sorted(chosen.values(),key=lambda r:(r['dateFiled'],r['form'],r['filename']))

def registrant_equivalent(candidate_norm, company_norm):
    def core(x):
        return x[4:] if x.startswith('THE ') else x
    return candidate_norm==company_norm or core(candidate_norm)==core(company_norm)

def prepare_binding_index(lines):
    norm_lines=[base.norm(line) for line in lines]
    token_lines=defaultdict(set)
    for i,n in enumerate(norm_lines):
        for token in set(n.split()):
            token_lines[token].add(i)
    marker_lines=[i for i,line in enumerate(lines) if strict.EXPLICIT_ETF_CLASS_LINE.search(line)]
    phrase_cache={}
    return {'normLines':norm_lines,'tokenLines':{k:tuple(sorted(v)) for k,v in token_lines.items()},'markerLines':marker_lines,'phraseCache':phrase_cache}

def phrase_norm(op_index,i,width):
    key=(i,width)
    cache=op_index['phraseCache']
    if key not in cache:
        cache[key]=base.norm(' '.join(op_index['normLines'][i:i+width]))
    return cache[key]

def classify_binding_indexed(title, normalized_title, registrant, op_index):
    parts=normalized_title.split()
    if not parts:
        return None,None
    candidate_lines=op_index['tokenLines'].get(parts[0],())
    hits=set()
    n=len(op_index['normLines'])
    for token_line in candidate_lines:
        for i in range(max(0,token_line-2),token_line+1):
            for width in (1,2,3):
                if i+width>n or not (i<=token_line<i+width):
                    continue
                if normalized_title in phrase_norm(op_index,i,width):
                    hits.add(i)
    if not hits:
        return None,None
    markers=op_index['markerLines']
    nearest=min((abs(i-j) for i in hits for j in markers),default=None)
    if strict.TITLE_ETF_SEMANTIC.search(title):
        return 'TITLE_EXPLICIT_ETF_SEMANTIC',nearest
    if strict.REGISTRANT_ETF_SEMANTIC.search(registrant):
        return 'REGISTRANT_EXPLICIT_ETF_SEMANTIC',nearest
    if nearest is not None and nearest<=strict.MAX_CLASS_LINE_DISTANCE:
        return 'LOCAL_EXPLICIT_ETF_CLASS_WITHIN_6_LINES',nearest
    return None,nearest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--shard',type=int,required=True);ap.add_argument('--shards',type=int,required=True);args=ap.parse_args()
    h2=json.loads(H2.read_text());h1=json.loads(H1.read_text());pref=json.loads(PREF.read_text())
    all_ciks=sorted(set(pref['positiveCiks']));assigned={c for i,c in enumerate(all_ciks) if i%args.shards==args.shard}
    rows=[r for r in h2['rows'] if r['cik'] in assigned]
    rows += [r for r in h1['rows'] if r['cik'] in assigned and r['dateFiled']<=SOURCE_CUTOFF]
    uniq={}
    for r in rows: uniq[(r.get('accession'),r['filename'])]=r
    rows=sorted(uniq.values(),key=lambda r:(r['dateFiled'],r['form'],r['cik'],r['filename']))
    source_ciks={r['cik'] for r in rows};pros,trs=base.load_prospectus(source_ciks)
    ops=defaultdict(list);pros_audit=[]
    for cik in sorted(source_ciks):
        for f in prospectus_set(pros.get(cik,[])):
            rec={**f,'submissionUrl':base.su(f['filename'])}
            try:
                text,tr,_,prior=base.ft(rec['submissionUrl'],5_000_000,24);c=base.rule.find(base.rule.CREATION,text);e=base.rule.find(base.rule.EXCHANGE,text);lines=h2diag.line_text(text).splitlines()
                rec.update({'transport':tr,'priorErrors':prior,'creationIssuerOwnEvidence':bool(c),'exchangeIssuerOwnEvidence':bool(e),'lineCount':len(lines)})
                if c and e:
                    ops[cik].append({'dateFiled':f['dateFiled'],'form':f['form'],'filename':f['filename'],'bindingIndex':prepare_binding_index(lines)})
            except Exception as ex: rec.update({'error':type(ex).__name__,'errorDetail':str(ex)[:700]})
            pros_audit.append(rec)
    occurrences={};audit=[]
    binding_cache={}
    for r in rows:
        rec={k:r.get(k) for k in ('cik','company','form','dateFiled','accession','filename')}
        try:
            sub,tr=h2diag.fetch(r['filename']);primary,desc,text,doctype=h2diag.primary_document(sub,r['form']);windows=h2diag.marker_windows(text)
            rec.update({'transport':tr,'primaryDocument':primary,'primaryDocumentType':doctype,'documentDescription':desc,'scheduleMarkerCount':len(windows),'hasCompletePortfolioSchedule':bool(windows)})
            matches=[]
            company_norm=base.norm(r['company'])
            for w in windows:
                best=None
                for candidate in strict.title_candidates(w):
                    if registrant_equivalent(candidate['normalizedTitle'],company_norm):
                        continue
                    proposals=[]
                    for op in ops.get(r['cik'],[]):
                        cache_key=(r['cik'],candidate['title'],candidate['normalizedTitle'],r['company'],op['filename'])
                        if cache_key not in binding_cache:
                            binding_cache[cache_key]=classify_binding_indexed(candidate['title'],candidate['normalizedTitle'],r['company'],op['bindingIndex'])
                        binding,distance=binding_cache[cache_key]
                        if not binding: continue
                        proposals.append({**candidate,'binding':binding,'explicitEtfClassLineDistance':distance,'evidenceDateFiled':op['dateFiled'],'evidenceForm':op['form'],'evidenceFilename':op['filename']})
                    if not proposals: continue
                    p=min(proposals,key=lambda x:(x['evidenceDateFiled'],x['evidenceFilename'],x['binding']))
                    if best is None or (len(p['normalizedTitle'].split()),len(p['normalizedTitle']))>(len(best['normalizedTitle'].split()),len(best['normalizedTitle'])):best=p
                if best:
                    key=f"LEGACY:{r['cik']}:{hashlib.sha1(best['normalizedTitle'].encode()).hexdigest()[:12].upper()}";item={'legacyIdentity':key,'cik':r['cik'],'registrant':r['company'],'seriesName':best['title'],'normalizedSeriesName':best['normalizedTitle'],'sourceAccession':r.get('accession'),'sourceFilingDate':r['dateFiled'],'sourceForm':r['form'],'sourceFilename':r['filename'],'evidenceDateFiled':best['evidenceDateFiled'],'evidenceForm':best['evidenceForm'],'evidenceFilename':best['evidenceFilename'],'binding':best['binding'],'explicitEtfClassLineDistance':best['explicitEtfClassLineDistance']}
                    occurrences[(key,r.get('accession') or r['filename'])]=item;matches.append({**best,'markerIndex':w['markerIndex']})
            rec['matchedMarkerCount']=len(matches);rec['matchedLegacySeriesNames']=sorted({m['normalizedTitle'] for m in matches})
        except Exception as ex:rec.update({'error':type(ex).__name__,'errorDetail':str(ex)[:900]})
        audit.append(rec);print('SOURCE',json.dumps({k:rec.get(k) for k in ('cik','form','dateFiled','scheduleMarkerCount','matchedMarkerCount','error')}),flush=True)
    occ=list(occurrences.values());identities={}
    for r in sorted(occ,key=lambda x:(x['evidenceDateFiled'],x['legacyIdentity'],x['evidenceFilename'])): identities.setdefault(r['legacyIdentity'],r)
    snaps=[]
    for month,asof in MONTHS:
        latest={}
        for r in occ:
            if r['sourceFilingDate']>asof or r['evidenceDateFiled']>asof:continue
            cur=latest.get(r['legacyIdentity'])
            if cur is None or (r['sourceFilingDate'],r['sourceAccession'] or '')>(cur['sourceFilingDate'],cur['sourceAccession'] or ''):latest[r['legacyIdentity']]=r
        src=sorted(latest.values(),key=lambda x:(x['cik'],x['normalizedSeriesName']))
        snaps.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(src),'sourceFilings':src})
    binding=Counter(r['binding'] for r in identities.values());forms=Counter(r['sourceForm'] for r in occ)
    out={'purpose':'Shard of strict pre-Series-ID complete-portfolio ETF source catalog. Selection semantics are identical to the monolithic resolver except that a normalized title equivalent to the SEC registrant/company name, including a leading THE decoration on either side, is explicitly rejected as a non-Series identity. CIK modulo partitioning only changes execution topology. Binding classification is memoized by exact candidate/evidence-filing inputs. Prospectus normalized lines, token-to-line lookup, phrase normalization, and ETF-class marker lines are indexed once per evidence filing; the accepted substring, semantic, and six-line tests remain unchanged. These changes affect execution cost only, not selection semantics.','seriesIdMandatoryDate':SERIES_ID_START,'sourceCutoff':SOURCE_CUTOFF,'evidenceCutoff':EVIDENCE_CUTOFF,'shard':args.shard,'shards':args.shards,'assignedCiks':sorted(assigned),'candidateSourceFilingCount':len(rows),'candidateRegistrantWithSourceFilingCount':len(source_ciks),'operationalEvidenceFilingCount':sum(len(v) for v in ops.values()),'positiveIdentityCount':len(identities),'bindingCounts':dict(sorted(binding.items())),'sourceOccurrenceCount':len(occ),'sourceFormCounts':dict(sorted(forms.items())),'sourceNoScheduleCount':sum('error' not in x and not x.get('hasCompletePortfolioSchedule',False) for x in audit),'amendmentNoScheduleCount':sum(str(x.get('form','')).endswith('/A') and 'error' not in x and not x.get('hasCompletePortfolioSchedule',False) for x in audit),'prospectusErrorCount':sum('error' in x for x in pros_audit),'sourceErrorCount':sum('error' in x for x in audit),'positiveIdentities':sorted(identities.values(),key=lambda x:x['legacyIdentity']),'sourceOccurrences':sorted(occ,key=lambda x:(x['legacyIdentity'],x['sourceFilingDate'],x['sourceAccession'] or '')),'monthSnapshots':snaps,'prospectusAudit':pros_audit,'sourceAudit':audit,'masterTransports':trs}
    outp=ROOT/f'data/research/sec-legacy-etf-series-source-preid-2006-shard-{args.shard}.json';outp.parent.mkdir(parents=True,exist_ok=True);outp.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('positiveIdentities','sourceOccurrences','monthSnapshots','prospectusAudit','sourceAudit','masterTransports')}),flush=True)
if __name__=='__main__':main()
