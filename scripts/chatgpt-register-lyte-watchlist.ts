import fs from 'node:fs';
const path='data/universe-watchlist.json';
const data=JSON.parse(fs.readFileSync(path,'utf8'));
const entries=data.entries as any[];
for (const s of ['CIEN','AXTI']) if (entries.some(e=>e.symbol===s)) throw new Error(`${s} already exists`);
entries.push({symbol:'CIEN',genre:'Optical Networking',track:'candidate',priority:'A',status:'watch',discoveryDate:'2026-08-22',rationale:'AI data-center optical networking candidate with direct exposure to coherent optics, 800G/1.6T and CPO infrastructure; strong strategic relevance warrants forward monitoring.',sanityCheck:{selectedMonths:9,changedMonths:9,cagr:1.3452580410446915,deltaCagr:0.06858479724715494,maxDrawdown:-0.23405456767467692,annualizedVolatility:0.5354738222306387,calmar:5.747625668705286},forwardEvidence:{startDate:'2026-08-22',completedObservations:0}});
entries.push({symbol:'AXTI',genre:'Optical Networking',track:'candidate',priority:'B',status:'watch',discoveryDate:'2026-08-22',rationale:'InP compound-semiconductor substrate supplier tied to AI optical connectivity demand; forward monitoring is warranted given strong theme exposure but higher historical drawdown and volatility.',sanityCheck:{selectedMonths:14,changedMonths:14,cagr:1.4477364316240222,deltaCagr:0.17106318782648566,maxDrawdown:-0.2548518782493119,annualizedVolatility:0.5596177390092896,calmar:5.680697515628105},forwardEvidence:{startDate:'2026-08-22',completedObservations:0}});
data.updatedAt='2026-08-22';
fs.writeFileSync(path,JSON.stringify(data,null,2)+'\n');
