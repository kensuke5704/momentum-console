import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { UniverseMonth } from "../src/lib/types";

type UniverseFile = { history: UniverseMonth[] };
type SameDay = { signalMonth:string; signalDate:string; accession:string; seriesId:string; seriesName:string; filingDate:string };
type AuditRow = SameDay & { acceptedAtET:string|null; acceptedCompact:string|null; status:"BEFORE_13_ET"|"BETWEEN_13_16_ET"|"AFTER_16_ET"|"FAILED"; secUrl:string };

const UA = process.env.SEC_USER_AGENT ?? "MomentumConsole/2.0 kensuke5704@users.noreply.github.com";
const sleep=(ms:number)=>new Promise(r=>setTimeout(r,ms));

function secTextUrl(accession:string){
  const clean=accession.replace(/-/g,"");
  const cik=String(Number(accession.slice(0,10)));
  return `https://www.sec.gov/Archives/edgar/data/${cik}/${clean}/${accession}.txt`;
}

async function getAcceptance(accession:string):Promise<{compact:string|null,url:string}> {
  const url=secTextUrl(accession);
  for(let attempt=0;attempt<4;attempt++){
    const res=await fetch(url,{headers:{"User-Agent":UA,Accept:"text/plain,*/*"},signal:AbortSignal.timeout(30000)}).catch(()=>null);
    if(res?.ok){
      const text=await res.text();
      const m=/<ACCEPTANCE-DATETIME>\s*(\d{14})/i.exec(text);
      return {compact:m?.[1]??null,url};
    }
    await sleep(700*(attempt+1));
  }
  return {compact:null,url};
}

function formatET(v:string|null){
  if(!v)return null;
  return `${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6,8)} ${v.slice(8,10)}:${v.slice(10,12)}:${v.slice(12,14)} ET`;
}
function classify(v:string|null):AuditRow["status"]{
  if(!v)return "FAILED";
  const hhmmss=Number(v.slice(8));
  if(hhmmss<130000)return "BEFORE_13_ET";
  if(hhmmss<160000)return "BETWEEN_13_16_ET";
  return "AFTER_16_ET";
}

async function main(){
  const uf=JSON.parse(await readFile(resolve("public/data/universe-history.json"),"utf8")) as UniverseFile;
  const same:SameDay[]=[];
  for(const u of uf.history){
    for(const f of u.sourceFilings){
      if(f.filingDate===u.asOf) same.push({signalMonth:u.signalMonth,signalDate:u.asOf,...f});
    }
  }
  const unique=[...new Map(same.map(x=>[`${x.signalDate}|${x.accession}`,x])).values()];
  const rows:AuditRow[]=[];
  for(let i=0;i<unique.length;i++){
    const f=unique[i];
    const got=await getAcceptance(f.accession);
    rows.push({...f,acceptedCompact:got.compact,acceptedAtET:formatET(got.compact),status:classify(got.compact),secUrl:got.url});
    if((i+1)%20===0) console.log(`checked ${i+1}/${unique.length}`);
    await sleep(140);
  }
  const counts=Object.fromEntries(["BEFORE_13_ET","BETWEEN_13_16_ET","AFTER_16_ET","FAILED"].map(s=>[s,rows.filter(r=>r.status===s).length]));
  const impactedMonths=[...new Set(rows.filter(r=>r.status==="AFTER_16_ET"||r.status==="BETWEEN_13_16_ET").map(r=>r.signalMonth))];
  const out={generatedAt:new Date().toISOString(),definition:{sameDay:"source filingDate equals Universe signal close date",classification:"<13:00 ET definitely pre-close; 13:00-15:59:59 ET requires early-close-calendar check; >=16:00 ET unavailable by regular close"},totalSameDaySourceFilings:same.length,uniqueSameDayAccessions:unique.length,counts,impactedMonths,rows};
  await mkdir(resolve("data/research/execution-feasibility"),{recursive:true});
  await writeFile(resolve("data/research/execution-feasibility/nport-acceptance.json"),JSON.stringify(out,null,2));
  console.log("NPORT_ACCEPTANCE_SUMMARY="+JSON.stringify({totalSameDaySourceFilings:same.length,uniqueSameDayAccessions:unique.length,counts,impactedMonths,after16:rows.filter(r=>r.status==="AFTER_16_ET").map(r=>({month:r.signalMonth,date:r.signalDate,accession:r.accession,series:r.seriesName,accepted:r.acceptedAtET})),between13and16:rows.filter(r=>r.status==="BETWEEN_13_16_ET").map(r=>({month:r.signalMonth,date:r.signalDate,accession:r.accession,series:r.seriesName,accepted:r.acceptedAtET})),failed:rows.filter(r=>r.status==="FAILED").map(r=>({date:r.signalDate,accession:r.accession,series:r.seriesName}))}));
}
main().catch(e=>{console.error(e);process.exit(1)});
