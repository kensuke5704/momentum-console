import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { UniverseMonth } from "../src/lib/types";
import { fetchYahooHistory } from "../src/lib/yahoo";

type UniverseFile = { history: UniverseMonth[] };
type SameDay = { signalMonth:string; signalDate:string; accession:string; seriesId:string; seriesName:string; filingDate:string };
type AuditRow = SameDay & {
  acceptedAtET:string|null;
  acceptedCompact:string|null;
  nextSessionDate:string|null;
  nominalLeadHours:number|null;
  status:"BEFORE_NEXT_OPEN"|"WITHIN_2H_OF_OPEN"|"AT_OR_AFTER_NEXT_OPEN"|"FAILED";
  secUrl:string;
};

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
    await sleep(800*(attempt+1));
  }
  return {compact:null,url};
}

function formatET(v:string|null){
  if(!v)return null;
  return `${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6,8)} ${v.slice(8,10)}:${v.slice(10,12)}:${v.slice(12,14)} ET`;
}

function compactToNaiveEtMs(v:string){
  return Date.UTC(
    Number(v.slice(0,4)), Number(v.slice(4,6))-1, Number(v.slice(6,8)),
    Number(v.slice(8,10)), Number(v.slice(10,12)), Number(v.slice(12,14)),
  );
}
function nextOpenNaiveEtMs(date:string){
  const [y,m,d]=date.split("-").map(Number);
  return Date.UTC(y,m-1,d,9,30,0);
}

async function main(){
  const uf=JSON.parse(await readFile(resolve("public/data/universe-history.json"),"utf8")) as UniverseFile;
  const same:SameDay[]=[];
  for(const u of uf.history) for(const f of u.sourceFilings) if(f.filingDate===u.asOf) same.push({signalMonth:u.signalMonth,signalDate:u.asOf,...f});
  const unique=[...new Map(same.map(x=>[`${x.signalDate}|${x.accession}`,x])).values()];

  const qqq=await fetchYahooHistory("QQQ");
  const sessions=qqq.map(p=>p.date).sort();
  const nextSessionByDate=new Map<string,string>();
  for(const f of unique){
    const next=sessions.find(d=>d>f.signalDate) ?? null;
    if(next) nextSessionByDate.set(f.signalDate,next);
  }

  const rows:Array<AuditRow|undefined>=new Array(unique.length);
  let cursor=0, done=0;
  async function worker(){
    while(true){
      const i=cursor++; if(i>=unique.length)return;
      const f=unique[i];
      const got=await getAcceptance(f.accession);
      const nextSessionDate=nextSessionByDate.get(f.signalDate) ?? null;
      let nominalLeadHours:number|null=null;
      let status:AuditRow["status"]="FAILED";
      if(got.compact && nextSessionDate){
        nominalLeadHours=(nextOpenNaiveEtMs(nextSessionDate)-compactToNaiveEtMs(got.compact))/3_600_000;
        if(nominalLeadHours<=0) status="AT_OR_AFTER_NEXT_OPEN";
        else if(nominalLeadHours<2) status="WITHIN_2H_OF_OPEN";
        else status="BEFORE_NEXT_OPEN";
      }
      rows[i]={...f,acceptedCompact:got.compact,acceptedAtET:formatET(got.compact),nextSessionDate,nominalLeadHours,status,secUrl:got.url};
      done++; if(done%20===0||done===unique.length)console.log(`checked ${done}/${unique.length}`);
      await sleep(650);
    }
  }
  await Promise.all(Array.from({length:6},()=>worker()));
  const complete=rows.filter((x):x is AuditRow=>Boolean(x));
  const statuses=["BEFORE_NEXT_OPEN","WITHIN_2H_OF_OPEN","AT_OR_AFTER_NEXT_OPEN","FAILED"] as const;
  const counts=Object.fromEntries(statuses.map(s=>[s,complete.filter(r=>r.status===s).length]));
  const validLead=complete.filter(r=>r.nominalLeadHours!==null).sort((a,b)=>a.nominalLeadHours!-b.nominalLeadHours!);
  const out={
    generatedAt:new Date().toISOString(),
    definition:{
      universeCandidate:"source filingDate equals Universe signal close date",
      availabilityRule:"EDGAR ACCEPTANCE-DATETIME must be earlier than 09:30 ET on the next actual QQQ trading session",
      practicalBuffer:"flag filings accepted less than 2 hours before next open",
      note:"Lead hours use ET wall-clock arithmetic; DST boundary can shift elapsed time by one hour, but does not affect before/after-open classification because both endpoints are compared in ET."
    },
    totalSameDaySourceFilings:same.length,
    uniqueSameDayAccessions:unique.length,
    counts,
    minimumLead:validLead[0] ? {signalMonth:validLead[0].signalMonth,signalDate:validLead[0].signalDate,series:validLead[0].seriesName,accession:validLead[0].accession,acceptedAtET:validLead[0].acceptedAtET,nextSessionDate:validLead[0].nextSessionDate,nominalLeadHours:validLead[0].nominalLeadHours} : null,
    violations:complete.filter(r=>r.status==="AT_OR_AFTER_NEXT_OPEN"),
    nearOpen:complete.filter(r=>r.status==="WITHIN_2H_OF_OPEN"),
    failed:complete.filter(r=>r.status==="FAILED"),
    rows:complete
  };
  await mkdir(resolve("data/research/execution-feasibility"),{recursive:true});
  await writeFile(resolve("data/research/execution-feasibility/nport-next-open-audit.json"),JSON.stringify(out,null,2));
  console.log("NPORT_NEXT_OPEN_SUMMARY="+JSON.stringify({uniqueSameDayAccessions:unique.length,counts,minimumLead:out.minimumLead,violations:out.violations.map(r=>({month:r.signalMonth,date:r.signalDate,accession:r.accession,series:r.seriesName,accepted:r.acceptedAtET,next:r.nextSessionDate,lead:r.nominalLeadHours})),nearOpen:out.nearOpen.map(r=>({month:r.signalMonth,date:r.signalDate,accession:r.accession,series:r.seriesName,accepted:r.acceptedAtET,next:r.nextSessionDate,lead:r.nominalLeadHours})),failed:out.failed.map(r=>({date:r.signalDate,accession:r.accession,series:r.seriesName}))}));
}
main().catch(e=>{console.error(e);process.exit(1)});
