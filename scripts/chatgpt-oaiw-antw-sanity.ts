import { TICKERS } from "../src/lib/config";
import { FROZEN_STRATEGY, FROZEN_STRATEGY_ID } from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import { fetchHistories } from "../src/lib/yahoo";
import type { TickerConfig } from "../src/lib/types";

function calmar(cagr:number, dd:number){ return dd < 0 ? cagr / Math.abs(dd) : 0; }
function same(a:string[],b:string[]){ return [...a].sort().join("|") === [...b].sort().join("|"); }

async function main(){
  const candidates:TickerConfig[]=[
    {symbol:"WULF",genre:"AI Infrastructure"},{symbol:"HUT",genre:"AI Infrastructure"},
    {symbol:"AMD",genre:"AI Semi"},{symbol:"AVGO",genre:"AI Semi"},
    {symbol:"ORCL",genre:"AI Infrastructure"},{symbol:"IREN",genre:"AI Infrastructure"},
    {symbol:"CORZ",genre:"AI Infrastructure"},
  ];
  const prod=new Set(TICKERS.map(x=>x.symbol));
  for(const c of candidates) if(prod.has(c.symbol)) throw new Error(`${c.symbol} already production`);
  const symbols=[...new Set([...TICKERS.map(x=>x.symbol),...candidates.map(x=>x.symbol)])];
  const histories=await fetchHistories(symbols);
  const baseline=buildDashboard(histories,TICKERS,FROZEN_STRATEGY);
  const bRows=new Map(baseline.backtest.rows.map(r=>[r.signalMonth,r]));
  const bs=baseline.backtest.stats;
  const out:any={strategyId:FROZEN_STRATEGY_ID,baseline:{cagr:bs.cagr,maxDrawdown:bs.maxDrawdown,annualizedVolatility:bs.annualizedVolatility,calmar:calmar(bs.cagr,bs.maxDrawdown)},candidates:[]};
  for(const c of candidates){
    const s=buildDashboard(histories,[...TICKERS,c],FROZEN_STRATEGY); const st=s.backtest.stats;
    const sel=s.backtest.rows.filter(r=>r.picks.includes(c.symbol));
    const changed=s.backtest.rows.filter(r=>{const b=bRows.get(r.signalMonth); return b ? !same(b.picks,r.picks):false;});
    const returns=sel.map(r=>{ if(!r.entryDate||!r.exitDate) return null; const h=histories[c.symbol]; const e=h.find(p=>p.date>=r.entryDate!); const x=h.find(p=>p.date>=r.exitDate!); return e&&x ? x.close/e.close-1 : null; }).filter((x):x is number=>typeof x==='number');
    const displaced=new Map<string,number>();
    const detail=sel.map(r=>{const b=bRows.get(r.signalMonth); const rem=b?b.picks.filter(x=>!r.picks.includes(x)):[]; rem.forEach(x=>displaced.set(x,(displaced.get(x)??0)+1)); return {signalMonth:r.signalMonth,entryDate:r.entryDate,exitDate:r.exitDate,candidateReturn:(()=>{if(!r.entryDate||!r.exitDate)return null;const h=histories[c.symbol];const e=h.find(p=>p.date>=r.entryDate!);const x=h.find(p=>p.date>=r.exitDate!);return e&&x?x.close/e.close-1:null;})(),displaced:rem};});
    out.candidates.push({symbol:c.symbol,genre:c.genre,selectedMonths:sel.length,changedMonths:changed.length,cagr:st.cagr,deltaCagr:st.cagr-bs.cagr,maxDrawdown:st.maxDrawdown,deltaMaxDrawdown:st.maxDrawdown-bs.maxDrawdown,annualizedVolatility:st.annualizedVolatility,deltaAnnualizedVolatility:st.annualizedVolatility-bs.annualizedVolatility,calmar:calmar(st.cagr,st.maxDrawdown),deltaCalmar:calmar(st.cagr,st.maxDrawdown)-calmar(bs.cagr,bs.maxDrawdown),averageSelectedHoldingReturn:returns.length?returns.reduce((a,b)=>a+b,0)/returns.length:null,selectedWinRate:returns.length?returns.filter(x=>x>0).length/returns.length:null,worstSelectedHoldingReturn:returns.length?Math.min(...returns):null,bestSelectedHoldingReturn:returns.length?Math.max(...returns):null,displacedTickers:[...displaced.entries()],selectedDetail:detail});
  }
  console.log("OAIW_ANTW_SANITY_JSON_START"); console.log(JSON.stringify(out,null,2)); console.log("OAIW_ANTW_SANITY_JSON_END");
}
main().catch(e=>{console.error(e);process.exitCode=1;});
