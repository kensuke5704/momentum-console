import type {EquityPoint,PricePoint,UniverseMonth} from "../types";

const mean=(values:number[])=>values.reduce((sum,value)=>sum+value,0)/(values.length||1);
function latestUniverse(universe:UniverseMonth[],date:string){let latest:UniverseMonth|null=null;for(const row of universe){if(row.asOf<=date)latest=row;else break}return latest}

/**
 * Frozen Candidate-G breakout engine. Stage21 does not fund G; this curve is
 * retained only inside the pre-existing M3 shadow-core risk measurement.
 */
export function runBreakoutShadow(histories:Record<string,PricePoint[]>,universeHistory:UniverseMonth[],start="2020-01-01",end="9999-12-31"):EquityPoint[]{
 const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));
 const dates=qqq.map(x=>x.date).filter(date=>date>=start&&date<=end);
 const rows=Object.fromEntries(Object.entries(histories).map(([symbol,points])=>[symbol,[...points].sort((a,b)=>a.date.localeCompare(b.date))]));
 const indexes=Object.fromEntries(Object.entries(rows).map(([symbol,points])=>[symbol,new Map((points as PricePoint[]).map((point,index)=>[point.date,index]))]));
 const maps=Object.fromEntries(Object.entries(rows).map(([symbol,points])=>[symbol,new Map((points as PricePoint[]).map(point=>[point.date,point]))]));
 let cash=1,positions:Array<{symbol:string;shares:number;entry:number}>=[],pendingEntry:{date:string;symbols:string[]}|null=null,pendingExit:string|null=null,hold=0,peak=1;
 const curve:EquityPoint[]=[];
 const equity=(date:string,field:"open"|"close")=>cash+positions.reduce((sum,p)=>sum+p.shares*((maps[p.symbol] as Map<string,PricePoint>).get(date)?.[field]??p.entry),0);
 for(let di=0;di<dates.length;di++){
  const date=dates[di],next=dates[di+1]??null;
  if(pendingExit===date&&positions.length){cash=positions.reduce((sum,p)=>{const row=(maps[p.symbol] as Map<string,PricePoint>).get(date);return sum+p.shares*(row?.open??row?.close??p.entry)},0)*.999;positions=[];pendingExit=null;hold=0;peak=cash}
  if(pendingEntry?.date===date&&!positions.length){const opens=pendingEntry.symbols.map(symbol=>(maps[symbol] as Map<string,PricePoint>).get(date)?.open);if(opens.length===5&&opens.every(value=>value&&value>0)){const per=cash/5;positions=pendingEntry.symbols.map((symbol,index)=>({symbol,shares:per*.999/(opens[index] as number),entry:opens[index] as number}));cash=0;peak=equity(date,"open");hold=0}pendingEntry=null}
  const value=equity(date,"close");peak=Math.max(peak,value);const drawdown=value/peak-1;curve.push({date,equity:value,drawdown});
  if(positions.length&&!pendingExit&&next){hold++;const stop=positions.some(p=>((maps[p.symbol] as Map<string,PricePoint>).get(date)?.close??Infinity)<=p.entry*.88);if(stop||drawdown<=-.15||hold>=20)pendingExit=next}
  if(!positions.length&&!pendingEntry&&next){const qi=(indexes.QQQ as Map<string,number>).get(date);if(qi==null||qi<199)continue;const qrows=rows.QQQ as PricePoint[];if(qrows[qi].close<=mean(qrows.slice(qi-199,qi+1).map(x=>x.close)))continue;const universe=latestUniverse(universeHistory,date);if(!universe)continue;const candidates:Array<{symbol:string;strength:number}>=[];for(const member of universe.symbols){const symbol=member.symbol,index=(indexes[symbol] as Map<string,number>|undefined)?.get(date),series=rows[symbol] as PricePoint[]|undefined;if(index==null||!series||index<99||index<20)continue;const close=series[index].close;if(close<=mean(series.slice(index-99,index+1).map(x=>x.close)))continue;const high=Math.max(...series.slice(index-20,index).map(x=>x.close));if(close>high)candidates.push({symbol,strength:close/high-1})}candidates.sort((a,b)=>b.strength-a.strength||a.symbol.localeCompare(b.symbol));if(candidates.length>=5)pendingEntry={date:next,symbols:candidates.slice(0,5).map(x=>x.symbol)}}
 }
 return curve;
}
