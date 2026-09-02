#!/usr/bin/env python3
import csv, io, json, urllib.request, zipfile

META='https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/TZM1QT'
UA={'User-Agent':'momentum-console research'}

def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=180) as r:
        return r.read()

obj=json.loads(get(META))
ver=obj['data']['latestVersion']
files=[]
by_name={}
for x in ver.get('files',[]):
    d=x.get('dataFile',{})
    row={'id':d.get('id'),'filename':d.get('filename'),'filesize':d.get('filesize'),'contentType':d.get('contentType'),'restricted':x.get('restricted',False),'description':x.get('description')}
    files.append(row); by_name[row['filename']]=row
print(json.dumps({'version':ver.get('versionNumber'),'releaseTime':ver.get('releaseTime'),'fileCount':len(files),'files':files},indent=2))

for name in ['lhr_submission.zip','hr_panel_2020.zip']:
    f=by_name[name]
    print(f'\nINSPECT {name} id={f["id"]} size={f["filesize"]}',flush=True)
    data=get(f'https://dataverse.harvard.edu/api/access/datafile/{f["id"]}')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        print('ZIPFILES',z.namelist()[:20])
        first=z.namelist()[0]
        with z.open(first) as raw:
            text=io.TextIOWrapper(raw,encoding='utf-8-sig',errors='replace',newline='')
            sample=[]
            for _ in range(5):
                line=text.readline()
                if not line: break
                sample.append(line.rstrip('\n'))
            print('SAMPLE')
            for line in sample: print(line[:4000])
