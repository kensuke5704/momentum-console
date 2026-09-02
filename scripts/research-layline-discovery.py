#!/usr/bin/env python3
import json, urllib.request

URL='https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/TZM1QT'
req=urllib.request.Request(URL,headers={'User-Agent':'momentum-console research'})
with urllib.request.urlopen(req,timeout=90) as r:
    obj=json.load(r)
ver=obj['data']['latestVersion']
files=[]
for x in ver.get('files',[]):
    d=x.get('dataFile',{})
    files.append({
        'id':d.get('id'),'filename':d.get('filename'),'filesize':d.get('filesize'),
        'contentType':d.get('contentType'),'md5':d.get('md5'),'restricted':x.get('restricted',False),
        'description':x.get('description')
    })
print(json.dumps({'version':ver.get('versionNumber'),'releaseTime':ver.get('releaseTime'),'fileCount':len(files),'files':files},indent=2))
