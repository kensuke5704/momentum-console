import type { CompanyProfile } from "./company-profile";

const headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",Accept:"application/json, text/plain, */*","Accept-Language":"en-US,en;q=0.9",Referer:"https://www.nasdaq.com/"};

function findDescription(value:unknown,depth=0):string|null{
  if(depth>7||value==null)return null;
  if(Array.isArray(value)){for(const child of value){const x=findDescription(child,depth+1);if(x)return x;}return null;}
  if(typeof value!=="object")return null;
  const r=value as Record<string,unknown>;
  for(const key of ["companyDescription","businessDescription","description","longBusinessSummary"]){
    const v=r[key];
    if(typeof v==="string"&&v.trim().length>=80)return v.trim();
    if(v&&typeof v==="object")for(const k of ["value","label","text"]){const s=(v as Record<string,unknown>)[k];if(typeof s==="string"&&s.trim().length>=80)return s.trim();}
  }
  for(const child of Object.values(r)){const x=findDescription(child,depth+1);if(x)return x;}
  return null;
}

async function translateJa(text:string):Promise<string|null>{
  try{
    const src=text.trim().slice(0,5000);if(!src)return null;
    const res=await fetch(`https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ja&dt=t&q=${encodeURIComponent(src)}`,{headers,signal:AbortSignal.timeout(15000)});
    if(!res.ok)return null;const body=await res.json() as unknown;
    if(!Array.isArray(body)||!Array.isArray(body[0]))return null;
    const out=body[0].map((x)=>Array.isArray(x)&&typeof x[0]==="string"?x[0]:"").join("").replace(/\s+/g," ").trim();
    return out.length>=80?out:null;
  }catch{return null;}
}

async function nasdaqSummary(symbol:string):Promise<string|null>{
  try{
    const res=await fetch(`https://api.nasdaq.com/api/company/${encodeURIComponent(symbol)}/company-profile`,{headers,signal:AbortSignal.timeout(15000)});
    if(!res.ok)return null;const body=await res.json() as unknown;const en=findDescription(body);return en?await translateJa(en):null;
  }catch{return null;}
}

export async function enrichCompanyProfiles(profiles:Record<string,CompanyProfile>,symbols:string[],concurrency=3):Promise<Record<string,CompanyProfile>>{
  const out={...profiles};let cursor=0;
  async function worker(){while(cursor<symbols.length){const symbol=symbols[cursor++];const p=out[symbol];if(!p)continue;const current=p.summary?.trim()??"";if(current.length>=180)continue;const summary=await nasdaqSummary(symbol);if(summary)out[symbol]={...p,summary,updatedAt:new Date().toISOString()};}}
  await Promise.all(Array.from({length:Math.min(concurrency,Math.max(1,symbols.length))},()=>worker()));return out;
}
