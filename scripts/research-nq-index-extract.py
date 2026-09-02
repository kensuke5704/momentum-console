#!/usr/bin/env python3
from __future__ import annotations
import csv, io, json, os, re, tempfile, urllib.request, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DRIVE='https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
OUT=ROOT/'data'/'research'/'nq-index-2006.json'
TARGET_FORMS={'N-Q','N-Q/A','N-CSR','N-CSRS','N-CSR/A','N-CSRS/A'}

def download(url:str,path:Path):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r, open(path,'wb') as f:
        total=0
        while True:
            b=r.read(1024*1024)
            if not b: break
            f.write(b); total+=len(b)
            if total%(50*1024*1024)<1024*1024: print(f'downloaded={total:,}',flush=True)
    print(f'download complete bytes={path.stat().st_size:,}',flush=True)

def decode_sample(z:zipfile.ZipFile,name:str,limit=200000):
    with z.open(name) as f: return f.read(limit).decode('utf-8','replace')

def parse_delimited(text:str):
    lines=[x for x in text.splitlines() if x.strip()]
    if not lines:return []
    for delim in ['|','\t',',']:
        if delim in lines[0]:
            try:return list(csv.DictReader(io.StringIO('\n'.join(lines)),delimiter=delim))
            except: pass
    return []

def normalize_row(row:dict):
    d={str(k).strip().lower().replace(' ','_'):str(v).strip() for k,v in row.items() if k is not None}
    def pick(*keys):
        for k in keys:
            if d.get(k): return d[k]
        return ''
    return {
      'cik':pick('cik','central_index_key'),
      'company':pick('company_name','company','name'),
      'form':pick('form_type','form','type'),
      'dateFiled':pick('date_filed','filing_date','date'),
      'filename':pick('filename','file_name','path','url','filing_url'),
    }

def main():
    with tempfile.TemporaryDirectory() as td:
        zp=Path(td)/'master.zip'; download(DRIVE,zp)
        with zipfile.ZipFile(zp) as z:
            names=z.namelist(); print('zip entries=',len(names)); print('first entries=',names[:40])
            # Prefer files whose names suggest master/form indexes or 2006.
            candidates=[n for n in names if not n.endswith('/') and re.search(r'(master|index|2006)',n,re.I)]
            print('candidate entries=',candidates[:100])
            hits=[]; inspected=[]
            for name in candidates[:250]:
                try:
                    sample=decode_sample(z,name)
                except Exception as e:
                    inspected.append({'name':name,'error':repr(e)}); continue
                inspected.append({'name':name,'sample':sample[:500].replace('\n',' ')})
                if 'N-Q' not in sample and 'N-CSR' not in sample: continue
                rows=parse_delimited(sample)
                for row in rows:
                    x=normalize_row(row)
                    if x['form'].upper() in TARGET_FORMS and (x['dateFiled'].startswith('2006') or '/2006/' in x['filename'] or '2006' in name): hits.append(x)
                # Standard EDGAR master.idx pipe layout may have preamble; parse linewise too.
                for line in sample.splitlines():
                    if '|N-Q|' not in line and '|N-CSR|' not in line and '|N-CSRS|' not in line: continue
                    p=line.split('|')
                    if len(p)>=5 and p[3].startswith('2006'):
                        hits.append({'cik':p[0].strip(),'company':p[1].strip(),'form':p[2].strip(),'dateFiled':p[3].strip(),'filename':p[4].strip()})
            # If candidates didn't expose schema, inspect small number of every file for diagnostics.
            if not hits:
                for name in names[:80]:
                    if name.endswith('/'):continue
                    if any(x['name']==name for x in inspected):continue
                    try:s=decode_sample(z,name,50000)
                    except:continue
                    inspected.append({'name':name,'sample':s[:500].replace('\n',' ')})
            # Deduplicate.
            uniq={ (x['cik'],x['form'],x['dateFiled'],x['filename']):x for x in hits }
            hits=sorted(uniq.values(),key=lambda x:(x['dateFiled'],x['cik'],x['form'],x['filename']))
            summary={'archiveBytes':zp.stat().st_size,'zipEntries':len(names),'targetYear':2006,'targetForms':sorted(TARGET_FORMS),'hitCount':len(hits),'formCounts':{},'firstHits':hits[:50],'inspected':inspected[:80]}
            for x in hits: summary['formCounts'][x['form']]=summary['formCounts'].get(x['form'],0)+1
            OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(summary,indent=2)+'\n')
            print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ('firstHits','inspected')}),flush=True)
            print('FIRST_HITS',json.dumps(hits[:20],indent=2),flush=True)

if __name__=='__main__':main()
