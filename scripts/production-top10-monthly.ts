import fs from 'node:fs/promises';
import path from 'node:path';
import {PRODUCTION_STRATEGY as P} from '../src/lib/config';
import {buildMonthlySignal} from '../src/lib/strategy/momentum';
import {nextUsTradingSession} from '../src/lib/trading-calendar';
import type {PricePoint,UniverseMonth} from '../src/lib/types';

async function main(){
  const market=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8')) as {histories:Record<string,PricePoint[]>};
  const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8')) as {history:UniverseMonth[]};
  const universe=[...uf.history].filter(x=>x.asOf>=P.backtestStart).sort((a,b)=>a.asOf.localeCompare(b.asOf));
  const qqq=market.histories.QQQ;
  const symbols=new Set<string>(); const monthly:any[]=[];
  for(const u of universe){
    const s:any=buildMonthlySignal({universe:u,histories:market.histories,qqq,nextSessionDate:nextUsTradingSession(u.asOf),config:P});
    const top10=s.candidates.filter((c:any)=>c.eligible&&c.score!=null).slice(0,10).map((c:any)=>({symbol:c.symbol,score:c.score}));
    top10.forEach((x:any)=>symbols.add(x.symbol));
    monthly.push({date:u.asOf,marketRiskOn:s.marketRiskOn,top10});
  }
  const out={generatedAt:new Date().toISOString(),strategyId:P.strategyId,momentum:P.momentum,count:symbols.size,symbols:[...symbols].sort(),monthly};
  const d=path.join(process.cwd(),'data/research/production-top10-monthly'); await fs.mkdir(d,{recursive:true});
  await fs.writeFile(path.join(d,'result.json'),JSON.stringify(out,null,2));
  console.log('PRODUCTION_TOP10_UNION',symbols.size);
}
main().catch(e=>{console.error(e);process.exit(1)});
