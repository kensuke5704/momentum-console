import {performanceStats,runStrategySimulation} from "../backtest";
import {cftcStatus,type CftcPositionRow} from "../cftc";
import {PRODUCTION_STRATEGY} from "../config";
import {PRODUCTION_PORTFOLIO,type PortfolioRegime} from "../portfolio-config";
import type {PortfolioHolding,PortfolioLiveState,PortfolioTarget} from "../portfolio-types";
import {buildMonthlySignal} from "../strategy/momentum";
import {runBreakoutShadow} from "../strategy/breakout-shadow";
import {initialEngineState,transitionDay} from "../strategy/state-machine";
import {nextUsTradingSession} from "../trading-calendar";
import type {BacktestResult,EquityPoint,LiveStrategyState,PricePoint,UniverseMonth} from "../types";

type FixedTarget={symbols:string[];weights:number[]};
type FixedSnap={date:string;equity:number;target:FixedTarget};
type RegimeRow={date:string;regime:PortfolioRegime;cftc:ReturnType<typeof cftcStatus>;m3:{deep:boolean;coreReturn20:number|null;qqqReturn20:number|null;gap:number|null;recoveryConfirm:number}};
const START=PRODUCTION_STRATEGY.backtestStart;
const mean=(values:number[])=>values.reduce((sum,value)=>sum+value,0)/(values.length||1);
const returns=(curve:EquityPoint[])=>{const out=new Map<string,number>();for(let i=1;i<curve.length;i++)out.set(curve[i].date,curve[i].equity/curve[i-1].equity-1);return out};
const targetKey=(target:FixedTarget)=>target.symbols.map((symbol,index)=>`${symbol}:${(target.weights[index]??0).toFixed(6)}`).join("|");

function fixedSnapshots(histories:Record<string,PricePoint[]>,universeHistory:UniverseMonth[]):{snaps:FixedSnap[];state:LiveStrategyState}{
 const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));
 const dates=qqq.map(point=>point.date),dateIndex=new Map(dates.map((date,index)=>[date,index]));
 const priceMaps=Object.fromEntries(Object.entries(histories).map(([symbol,points])=>[symbol,new Map(points.map(point=>[point.date,point]))]));
 const universeBySignalDate=new Map(universeHistory.map(month=>[month.asOf,month]));
 let state=initialEngineState(PRODUCTION_STRATEGY);const snaps:FixedSnap[]=[];
 for(let index=0;index<dates.length;index++){
  const date=dates[index];if(date<START)continue;const nextSessionDate=dates[index+1]??nextUsTradingSession(date),universe=universeBySignalDate.get(date);
  const signal=universe?buildMonthlySignal({universe,histories,qqq,nextSessionDate,config:PRODUCTION_STRATEGY}):null;
  const symbols=new Set(["QQQ",...state.currentPositions.map(position=>position.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(signal?.selectedSymbols??[])]);
  const prices=Object.fromEntries([...symbols].map(symbol=>[symbol,priceMaps[symbol]?.get(date)]));
  state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(dateIndex.get(date)??index)+1),monthlySignal:signal,nextSessionDate},PRODUCTION_STRATEGY);
  let target:FixedTarget;
  if(state.nextAction.executionDate===nextSessionDate&&(state.nextAction.type==="BUY_NEXT_OPEN"||state.nextAction.type==="MONTH_END_REBALANCE_NEXT_OPEN")) target={symbols:[...state.nextAction.symbols],weights:[...state.nextAction.targetWeights]};
  else if(state.nextAction.executionDate===nextSessionDate&&state.nextAction.type==="SELL_ALL_NEXT_OPEN") target={symbols:[],weights:[]};
  else target={symbols:state.currentPositions.map(position=>position.symbol),weights:state.currentPositions.map(position=>position.targetWeight)};
  snaps.push({date,equity:state.currentEquity,target});
 }
 return{snaps,state};
}

function shadowCore(fixed:EquityPoint[],g:EquityPoint[]):EquityPoint[]{
 const fr=returns(fixed),gr=returns(g),dates=fixed.slice(1).map(point=>point.date).filter(date=>gr.has(date));let equity=1,peak=1;const out:EquityPoint[]=[{date:fixed[0].date,equity:1,drawdown:0}];
 for(const date of dates){equity*=1+PRODUCTION_PORTFOLIO.m3.shadowFixed60Weight*(fr.get(date)??0)+PRODUCTION_PORTFOLIO.m3.shadowGWeight*(gr.get(date)??0);peak=Math.max(peak,equity);out.push({date,equity,drawdown:equity/peak-1})}
 return out;
}

function regimeRows(fixed:EquityPoint[],g:EquityPoint[],qqqInput:PricePoint[],cftcRows:CftcPositionRow[]):RegimeRow[]{
 const shadow=shadowCore(fixed,g),shadowIndex=new Map(shadow.map((point,index)=>[point.date,index]));
 const qqq=[...qqqInput].sort((a,b)=>a.date.localeCompare(b.date)).filter(point=>point.date>=START),qqqIndex=new Map(qqq.map((point,index)=>[point.date,index]));
 let deep=false,recoveryConfirm=0;const out:RegimeRow[]=[];
 for(const point of shadow){const ci=shadowIndex.get(point.date)!,si=Math.max(0,ci-1);let coreReturn20:number|null=null,qqqReturn20:number|null=null,gap:number|null=null,enter=false,exit=false;
  if(si>=PRODUCTION_PORTFOLIO.m3.lookbackSessions){const signalPoint=shadow[si],qi=qqqIndex.get(signalPoint.date);if(qi!=null&&qi>=PRODUCTION_PORTFOLIO.m3.lookbackSessions){const lookback=PRODUCTION_PORTFOLIO.m3.lookbackSessions;coreReturn20=signalPoint.equity/shadow[si-lookback].equity-1;qqqReturn20=qqq[qi].close/qqq[qi-lookback].close-1;gap=coreReturn20-qqqReturn20;enter=coreReturn20<PRODUCTION_PORTFOLIO.m3.enterCoreReturnBelow&&gap<=PRODUCTION_PORTFOLIO.m3.enterUnderperformanceVsQqq;if(deep){if(gap>PRODUCTION_PORTFOLIO.m3.exitUnderperformanceVsQqq)recoveryConfirm++;else recoveryConfirm=0;exit=recoveryConfirm>=PRODUCTION_PORTFOLIO.m3.exitConfirmationSessions}}}
  if(!deep&&enter){deep=true;recoveryConfirm=0}else if(deep&&exit){deep=false;recoveryConfirm=0}
  // M3 is intentionally evaluated from the prior completed shadow-core point.
  // CFTC availability is calendar based, however, so evaluate it at the
  // portfolio close represented by this row. Reusing the M3 signal date here
  // delayed a newly eligible weekly report by one additional trading session.
  const cftc=cftcStatus(cftcRows,point.date),regime:PortfolioRegime=deep?"DEEP":cftc.yellow?"YELLOW":"NORMAL";
  out.push({date:point.date,regime,cftc,m3:{deep,coreReturn20,qqqReturn20,gap,recoveryConfirm}});
 }
 return out;
}

function combinedTargets(regime:PortfolioRegime,fixed:FixedTarget):PortfolioTarget[]{
 const weights=PRODUCTION_PORTFOLIO.weights[regime],innerTotal=fixed.weights.reduce((sum,value)=>sum+value,0);const targets:PortfolioTarget[]=[];
 fixed.symbols.forEach((symbol,index)=>{const weight=weights.fixed60*(fixed.weights[index]??0);if(weight>0)targets.push({symbol,weight,role:"FIXED60"})});
 if(weights.gldm>0)targets.push({symbol:"GLDM",weight:weights.gldm,role:"DIVERSIFIER"});
 const cash=weights.cash+weights.fixed60*Math.max(0,1-innerTotal);if(cash>1e-9)targets.push({symbol:"CASH",weight:cash,role:"CASH"});
 return targets;
}

function simulateNextOpen(histories:Record<string,PricePoint[]>,snaps:FixedSnap[],regimes:RegimeRow[]):{backtest:BacktestResult;holdings:PortfolioHolding[]}{
 const maps=Object.fromEntries(Object.entries(histories).map(([symbol,points])=>[symbol,new Map(points.map(point=>[point.date,point]))]));
 const snapMap=new Map(snaps.map(snap=>[snap.date,snap])),regimeMap=new Map(regimes.map(row=>[row.date,row]));const dates=snaps.map(snap=>snap.date).filter(date=>regimeMap.has(date));
 let cash=1,positions=new Map<string,number>(),pending:{fixed:FixedTarget;regime:PortfolioRegime}|null=null,lastMonth="",lastRegime:PortfolioRegime|null=null,lastFixed="",peak=1;const curve:EquityPoint[]=[];const events:BacktestResult["events"]=[],lastClose=new Map<string,number>(),entryPrices=new Map<string,number>();
 const price=(symbol:string,date:string,field:"open"|"close")=>(maps[symbol] as Map<string,PricePoint>|undefined)?.get(date)?.[field];
 const equityAt=(date:string,field:"open"|"close")=>cash+[...positions].reduce((sum,[symbol,shares])=>sum+shares*(price(symbol,date,field)??lastClose.get(symbol)??0),0);
 for(let i=0;i<dates.length;i++){
  const date=dates[i];
  if(pending){const openEquity=equityAt(date,"open"),desired=combinedTargets(pending.regime,pending.fixed).filter(target=>target.symbol!=="CASH"),targetShares=new Map<string,number>();for(const target of desired){const open=price(target.symbol,date,"open");if(!open||open<=0)throw new Error(`Stage21 missing ${target.symbol} open on ${date}`);targetShares.set(target.symbol,openEquity*target.weight/open)}let traded=0;for(const symbol of new Set([...positions.keys(),...targetShares.keys()]))traded+=Math.abs((targetShares.get(symbol)??0)-(positions.get(symbol)??0))*(price(symbol,date,"open")??0);const cost=traded*PRODUCTION_PORTFOLIO.execution.transactionCost,totalTarget=[...targetShares].reduce((sum,[symbol,shares])=>sum+shares*(price(symbol,date,"open")??0),0);if(totalTarget+cost>openEquity){const scale=openEquity/(totalTarget+cost);for(const [symbol,shares] of targetShares)targetShares.set(symbol,shares*scale);const scaledTarget=[...targetShares].reduce((sum,[symbol,shares])=>sum+shares*(price(symbol,date,"open")??0),0);let scaledTrade=0;for(const symbol of new Set([...positions.keys(),...targetShares.keys()]))scaledTrade+=Math.abs((targetShares.get(symbol)??0)-(positions.get(symbol)??0))*(price(symbol,date,"open")??0);cash=openEquity-scaledTarget-scaledTrade*PRODUCTION_PORTFOLIO.execution.transactionCost}else cash=openEquity-totalTarget-cost;for(const symbol of new Set([...positions.keys(),...targetShares.keys()])){const previousShares=positions.get(symbol)??0,nextShares=targetShares.get(symbol)??0,open=price(symbol,date,"open")??0;if(nextShares<=0){entryPrices.delete(symbol);continue}if(nextShares>previousShares&&open>0){const priorCost=(entryPrices.get(symbol)??open)*previousShares;entryPrices.set(symbol,(priorCost+open*(nextShares-previousShares))/nextShares)}}positions=targetShares;events.push({date,type:"PORTFOLIO_REBALANCE_OPEN",symbols:[...positions.keys()],reason:`Stage21 ${pending.regime} target executed at next open`});pending=null}
  for(const symbol of positions.keys()){const close=price(symbol,date,"close");if(close!=null)lastClose.set(symbol,close)}
  const equity=equityAt(date,"close");peak=Math.max(peak,equity);curve.push({date,equity,drawdown:equity/peak-1});
  const snap=snapMap.get(date)!,row=regimeMap.get(date)!,month=date.slice(0,7),fixedKey=targetKey(snap.target),monthly=month!==lastMonth,changed=row.regime!==lastRegime||fixedKey!==lastFixed;
  if(monthly||changed){pending={fixed:snap.target,regime:row.regime};if(lastRegime&&row.regime!==lastRegime)events.push({date,type:"REGIME_CHANGE_CLOSE",symbols:[],reason:`${lastRegime} -> ${row.regime}`});lastMonth=month;lastRegime=row.regime;lastFixed=fixedKey}
 }
 const finalEquity=curve.at(-1)?.equity??0;
 const holdings=[...positions].map(([symbol,shares]):PortfolioHolding=>({symbol,entryPrice:entryPrices.get(symbol)??lastClose.get(symbol)??0,currentPrice:lastClose.get(symbol)??null,targetWeight:finalEquity>0?(shares*(lastClose.get(symbol)??0))/finalEquity:0,role:symbol==="GLDM"?"DIVERSIFIER":"FIXED60"}));
 return{backtest:{strategyId:PRODUCTION_PORTFOLIO.strategyId,equityCurve:curve,stats:performanceStats(curve),benchmark:null,events},holdings};
}

export function buildStage21Portfolio(histories:Record<string,PricePoint[]>,universeHistory:UniverseMonth[],cftcRows:CftcPositionRow[]):{backtest:BacktestResult;portfolioState:PortfolioLiveState;innerState:LiveStrategyState}{
 if(!(histories.GLDM??[]).length)throw new Error("Stage21 requires GLDM history");
 const {snaps,state:innerState}=fixedSnapshots(histories,universeHistory);if(snaps.length<2)throw new Error("Stage21 fixed snapshots are empty");
 const base=snaps[0].equity||1,fixedCurve=snaps.map(snap=>({date:snap.date,equity:snap.equity/base,drawdown:0}));let peak=0;for(const point of fixedCurve){peak=Math.max(peak,point.equity);point.drawdown=point.equity/peak-1}
 const g=runBreakoutShadow(histories,universeHistory,START,snaps.at(-1)!.date),regimes=regimeRows(fixedCurve,g,histories.QQQ??[],cftcRows),simulation=simulateNextOpen(histories,snaps,regimes),backtest=simulation.backtest;
 const latest=snaps.at(-1)!,previous=snaps.at(-2)!,regime=regimes.at(-1)!,previousRegime=regimes.at(-2),targets=combinedTargets(regime.regime,latest.target),latestDate=latest.date;
 const firstOosDate=latestDate===PRODUCTION_PORTFOLIO.oosStartDate,monthly=latestDate.slice(0,7)!==previous.date.slice(0,7),changed=regime.regime!==previousRegime?.regime||targetKey(latest.target)!==targetKey(previous.target),eligible=latestDate>=PRODUCTION_PORTFOLIO.oosStartDate;
 const rebalance=eligible&&(firstOosDate||monthly||changed),executionDate=rebalance?nextUsTradingSession(latestDate):null;
 const reason=!eligible?`Stage21 OOS starts ${PRODUCTION_PORTFOLIO.oosStartDate}`:firstOosDate?"Initial frozen Stage21 allocation":regime.regime!==previousRegime?.regime?`Regime changed ${previousRegime?.regime??"—"} -> ${regime.regime}`:targetKey(latest.target)!==targetKey(previous.target)?"Fixed60 funded target changed":monthly?"Monthly Stage21 rebalance":"Target unchanged";
 const portfolioState:PortfolioLiveState={strategyId:PRODUCTION_PORTFOLIO.strategyId,asOf:latestDate,regime:regime.regime,cftc:regime.cftc,m3:regime.m3,fixed60:{strategyId:PRODUCTION_STRATEGY.strategyId,riskState:innerState.state,symbols:latest.target.symbols,innerWeights:latest.target.weights},targets,holdings:simulation.holdings,nextAction:{type:rebalance?"REBALANCE_NEXT_OPEN":"HOLD",executionDate,targets,reason}};
 return{backtest,portfolioState,innerState};
}
