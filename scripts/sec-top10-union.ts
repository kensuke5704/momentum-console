import fs from 'node:fs/promises';
import path from 'node:path';
import { PRODUCTION_STRATEGY as BASE } from '../src/lib/config';
import { buildMonthlySignal } from '../src/lib/strategy/momentum';
import { nextUsTradingSession } from '../src/lib/trading-calendar';
import type { PricePoint, UniverseMonth } from '../src/lib/types';

const CONFIG:any={
  ...BASE,
  strategyId:'momentum-sec-top10-union-diagnostic',
  momentum:{...BASE.momentum,oneMonth:0,threeMonth:.25,sixMonth:.75},
  allocation:{...BASE.allocation,baseTop1Weight:.60,concentratedTop1Weight:.70,concentrationZGap:.25,maxTop1Weight:.70},
};

async function main(){
  const market=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8')) as {histories:Record<string,PricePoint[]>};
  const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8')) as {history:UniverseMonth[]};
  const universe=[...uf.history].filter(x=>x.asOf>=CONFIG.backtestStart).sort((a,b)=>a.asOf.localeCompare(b.asOf));
  const qqq=market.histories.QQQ;
  const union=new Set<string>();
  const monthly:any[]=[];
  for(const u of universe){
    const s:any=buildMonthlySignal({universe:u,histories:market.histories,qqq,nextSessionDate:nextUsTradingSession(u.asOf),config:CONFIG});
    const top10=s.candidates.filter((c:any)=>c.eligible&&c.score!=null).slice(0,10).map((c:any)=>c.symbol);
    top10.forEach((x:string)=>union.add(x));
    monthly.push({date:u.asOf,top10});
  }
  const symbols=[...union].sort();
  const out={generatedAt:new Date().toISOString(),config:{momentum:'0/25/75',topK:10,start:CONFIG.backtestStart},count:symbols.length,symbols,monthly};
  const dir=path.join(process.cwd(),'data/research/sec-top10-union');
  await fs.mkdir(dir,{recursive:true});
  await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(out,null,2));
  console.log('SEC_TOP10_UNION_COUNT',symbols.length);
  console.log('SEC_TOP10_UNION_SYMBOLS',symbols.join(','));
}
// research rerun 2026-08-30: rebuild PIT candidate union before external SEC acquisition
main().catch(e=>{console.error(e);process.exit(1)});
