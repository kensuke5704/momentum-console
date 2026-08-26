import { readFile } from 'node:fs/promises';
const uf=JSON.parse(await readFile('public/data/universe-history.json','utf8'));
const rows=[];
for(const u of uf.history) for(const f of u.sourceFilings) if(f.filingDate===u.asOf) rows.push({signalMonth:u.signalMonth,signalDate:u.asOf,accession:f.accession,seriesName:f.seriesName});
const unique=[...new Map(rows.map(x=>[`${x.signalDate}|${x.accession}`,x])).values()];
console.log('SAMEDAY_NPORT='+JSON.stringify({count:unique.length,rows:unique}));