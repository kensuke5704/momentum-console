#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHARDS=ROOT/'data'/'research'/'beancounter-2006-shards'
MASTER=ROOT/'data'/'research'/'nq-index-2006.json'
OUT=ROOT/'data'/'research'/'beancounter-2006-coverage.json'
TARGET={'N-Q','N-Q/A','N-CSR','N-CSR/A','N-CSRS','N-CSRS/A'}

def main():
    files=sorted(SHARDS.glob('beancounter-2006-shard-*.json'))
    print('shard files',len(files),flush=True)
    by_acc={}
    shard_summaries=[]
    for path in files:
        obj=json.loads(path.read_text())
        shard_summaries.append({k:v for k,v in obj.items() if k!='filings'})
        for f in obj.get('filings',[]):
            acc=f['accession']
            cur=by_acc.get(acc)
            if cur is None:
                cur={**f,'cusips':set(f.get('cusips',[]))};by_acc[acc]=cur
            else:
                cur['attachments']=cur.get('attachments',0)+f.get('attachments',0)
                cur['portfolioMarker']=bool(cur.get('portfolioMarker') or f.get('portfolioMarker'))
                cur['scheduleMarker']=bool(cur.get('scheduleMarker') or f.get('scheduleMarker'))
                cur['cusips'].update(f.get('cusips',[]))
                cur['cusipCount']=len(cur['cusips'])
    for f in by_acc.values():
        if isinstance(f.get('cusips'),set):f['cusips']=sorted(f['cusips'])
        f['cusipCount']=len(f.get('cusips',[]))

    master=json.loads(MASTER.read_text())
    master_by={x['filename'].rsplit('/',1)[-1].removesuffix('.txt'):x for x in master.get('filings',[]) if x.get('form','').upper() in TARGET}
    # BeanCounter accession includes dashes; master filename accession does not.
    def nodash(s):return s.replace('-','')
    master_norm={nodash(k):v for k,v in master_by.items()}
    bean_norm={nodash(k):v for k,v in by_acc.items()}
    common=set(master_norm)&set(bean_norm)
    missing=set(master_norm)-set(bean_norm)
    extra=set(bean_norm)-set(master_norm)

    form_master=Counter(x['form'] for x in master_norm.values())
    form_common=Counter(master_norm[k]['form'] for k in common)
    form_bean=Counter(x['form'] for x in bean_norm.values())
    rows=list(bean_norm.values())
    cusip_any=sum(x.get('cusipCount',0)>0 for x in rows)
    cusip10=sum(x.get('cusipCount',0)>=10 for x in rows)
    schedule=sum(bool(x.get('scheduleMarker')) for x in rows)
    portfolio=sum(bool(x.get('portfolioMarker')) for x in rows)

    result={
      'source':'bradfordlevy/BeanCounter raw train shards 143-164, EDGAR-derived',
      'year':2006,
      'shardCount':len(files),
      'masterIndexFilings':len(master_norm),
      'beanCounterUniqueTargetFilings':len(bean_norm),
      'matchedMasterFilings':len(common),
      'masterRecall':len(common)/len(master_norm) if master_norm else None,
      'beanPrecisionAgainstMaster':len(common)/len(bean_norm) if bean_norm else None,
      'missingFromBeanCounter':len(missing),
      'extraVsMaster':len(extra),
      'formCountsMaster':dict(form_master),
      'formCountsMatched':dict(form_common),
      'formCountsBeanCounter':dict(form_bean),
      'withPortfolioMarker':portfolio,
      'portfolioMarkerRate':portfolio/len(rows) if rows else None,
      'withScheduleMarker':schedule,
      'scheduleMarkerRate':schedule/len(rows) if rows else None,
      'withAnyValidCusip':cusip_any,
      'anyValidCusipRate':cusip_any/len(rows) if rows else None,
      'withAtLeast10ValidCusips':cusip10,
      'atLeast10ValidCusipsRate':cusip10/len(rows) if rows else None,
      'matchedWithAnyValidCusip':sum(bean_norm[k].get('cusipCount',0)>0 for k in common),
      'matchedWithAtLeast10ValidCusips':sum(bean_norm[k].get('cusipCount',0)>=10 for k in common),
      'missingExamples':[master_norm[k] for k in sorted(missing)[:30]],
      'extraExamples':[{'accession':bean_norm[k]['accession'],'date':bean_norm[k]['date'],'form':bean_norm[k]['form']} for k in sorted(extra)[:30]],
      'shardSummaries':shard_summaries,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(result,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in result.items() if k not in ('missingExamples','extraExamples','shardSummaries')}),flush=True)

if __name__=='__main__':main()
