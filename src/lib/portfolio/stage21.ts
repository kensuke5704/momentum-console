import {performanceStats} from "../backtest";
import {cftcStatus,type CftcPositionRow} from "../cftc";
import {PRODUCTION_STRATEGY} from "../config";
import {PRODUCTION_PORTFOLIO,type PortfolioRegime} from "../portfolio-config";
import type {PortfolioHolding,PortfolioLiveState,PortfolioTarget} from "../portfolio-types";
import {buildMonthlySignal} from "../strategy/momentum";
import {runBreakoutShadow} from "../strategy/breakout-shadow";
import {initialEngineState,transitionDay,type EngineState} from "../strategy/state-machine";
import {nextUsTradingSession} from "../trading-calendar";
import type {BacktestResult,EquityPoint,LiveStrategyState,PricePoint,UniverseMonth} from "../types";

type FixedTarget={symbols:string[];weights:number[]};
type FixedSnap={date:string;equity:number;target:FixedTarget};
type RegimeRow={date:string;regime:PortfolioRegime;cftc:ReturnType<typeof cftcStatus>;m3:{deep:boolean;coreReturn20:number|null;qqqReturn20:number|null;gap:number|null;recoveryConfirm:number}};
const START=PRODUCTION_STRATEGY.backtestStart;
const returns=(curve:EquityPoint[])=>{const out=new Map<string,number>();for(let i=1;i<curve.length;i++)out.set(curve[i].date,curve[i].equity/curve[i-1].equity-1);return out};
const targetKey=(target:FixedTarget)=>target.symbols.map((symbol,index)=>`${symbol}:${(target.weights[index]??0).toFixed(6)}`).join("|");

function fixedSnapshots(histories:Record<string,PricePoint[]>,universeHistory:UniverseMonth[]):{snaps:FixedSnap[];state:EngineState}{
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

type Stage21Pending={fixed:FixedTarget;regime:PortfolioRegime;executionDate:string|null;reason:string};
type Stage21EngineState={asOf:string;cash:number;positions:Record<string,number>;lastClose:Record<string,number>;entryPrices:Record<string,number>;portfolioPeak:number;currentEquity:number;drawdown:number;lastMonth:string;lastRegime:PortfolioRegime|null;lastFixed:string;pending:Stage21Pending|null;events:BacktestResult["events"]};
type Stage21DayInput={date:string;nextSessionDate:string|null;snap:FixedSnap;regime:RegimeRow;forceRebalance:boolean};

function initialStage21State():Stage21EngineState{return{asOf:"",cash:1,positions:{},lastClose:{},entryPrices:{},portfolioPeak:1,currentEquity:1,drawdown:0,lastMonth:"",lastRegime:null,lastFixed:"",pending:null,events:[]}}

function transitionStage21(previous:Stage21EngineState,input:Stage21DayInput,maps:Record<string,Map<string,PricePoint>>):Stage21EngineState{
 const state=structuredClone(previous),price=(symbol:string,field:"open"|"close")=>maps[symbol]?.get(input.date)?.[field],equityAt=(field:"open"|"close")=>state.cash+Object.entries(state.positions).reduce((sum,[symbol,shares])=>sum+shares*(price(symbol,field)??state.lastClose[symbol]??0),0);
 if(state.pending?.executionDate===input.date){const pending=state.pending,openEquity=equityAt("open"),desired=combinedTargets(pending.regime,pending.fixed).filter(target=>target.symbol!=="CASH"),targetShares:Record<string,number>={};for(const target of desired){const open=price(target.symbol,"open");if(!open||open<=0)throw new Error(`Stage21 missing ${target.symbol} open on ${input.date}`);targetShares[target.symbol]=openEquity*target.weight/open}let traded=0;for(const symbol of new Set([...Object.keys(state.positions),...Object.keys(targetShares)]))traded+=Math.abs((targetShares[symbol]??0)-(state.positions[symbol]??0))*(price(symbol,"open")??0);const cost=traded*PRODUCTION_PORTFOLIO.execution.transactionCost,totalTarget=Object.entries(targetShares).reduce((sum,[symbol,shares])=>sum+shares*(price(symbol,"open")??0),0);if(totalTarget+cost>openEquity){const scale=openEquity/(totalTarget+cost);for(const symbol of Object.keys(targetShares))targetShares[symbol]*=scale;const scaledTarget=Object.entries(targetShares).reduce((sum,[symbol,shares])=>sum+shares*(price(symbol,"open")??0),0);let scaledTrade=0;for(const symbol of new Set([...Object.keys(state.positions),...Object.keys(targetShares)]))scaledTrade+=Math.abs((targetShares[symbol]??0)-(state.positions[symbol]??0))*(price(symbol,"open")??0);state.cash=openEquity-scaledTarget-scaledTrade*PRODUCTION_PORTFOLIO.execution.transactionCost}else state.cash=openEquity-totalTarget-cost;for(const symbol of new Set([...Object.keys(state.positions),...Object.keys(targetShares)])){const previousShares=state.positions[symbol]??0,nextShares=targetShares[symbol]??0,open=price(symbol,"open")??0;if(nextShares<=0){delete state.entryPrices[symbol];continue}if(nextShares>previousShares&&open>0){const priorCost=(state.entryPrices[symbol]??open)*previousShares;state.entryPrices[symbol]=(priorCost+open*(nextShares-previousShares))/nextShares}}state.positions=targetShares;state.events.push({date:input.date,type:"PORTFOLIO_REBALANCE_OPEN",symbols:Object.keys(state.positions),reason:`Stage21 ${pending.regime} target executed at next open`});state.pending=null}
 for(const symbol of Object.keys(state.positions)){const close=price(symbol,"close");if(close!=null)state.lastClose[symbol]=close}
 state.asOf=input.date;state.currentEquity=equityAt("close");state.portfolioPeak=Math.max(state.portfolioPeak,state.currentEquity);state.drawdown=state.portfolioPeak>0?state.currentEquity/state.portfolioPeak-1:0;
 const month=input.date.slice(0,7),fixedKey=targetKey(input.snap.target),monthly=month!==state.lastMonth,changed=input.regime.regime!==state.lastRegime||fixedKey!==state.lastFixed;
 if(monthly||changed||input.forceRebalance){const initial=state.lastRegime===null,reason=input.forceRebalance?"Initial frozen Stage21 allocation":initial?"Initial Stage21 allocation":input.regime.regime!==state.lastRegime?`Regime changed ${state.lastRegime} -> ${input.regime.regime}`:fixedKey!==state.lastFixed?"Fixed60 funded target changed":"Monthly Stage21 rebalance";state.pending={fixed:input.snap.target,regime:input.regime.regime,executionDate:input.nextSessionDate,reason};if(state.lastRegime&&input.regime.regime!==state.lastRegime)state.events.push({date:input.date,type:"REGIME_CHANGE_CLOSE",symbols:[],reason:`${state.lastRegime} -> ${input.regime.regime}`})}state.lastMonth=month;state.lastRegime=input.regime.regime;state.lastFixed=fixedKey;
 return state;
}

function simulateStage21(histories:Record<string,PricePoint[]>,snaps:FixedSnap[],regimes:RegimeRow[]):{backtest:BacktestResult;state:Stage21EngineState;holdings:PortfolioHolding[]}{
 const maps=Object.fromEntries(Object.entries(histories).map(([symbol,points])=>[symbol,new Map(points.map(point=>[point.date,point]))]));const snapMap=new Map(snaps.map(snap=>[snap.date,snap])),regimeMap=new Map(regimes.map(row=>[row.date,row])),dates=snaps.map(snap=>snap.date).filter(date=>regimeMap.has(date));let state=initialStage21State();const curve:EquityPoint[]=[];
 for(let index=0;index<dates.length;index++){const date=dates[index],snap=snapMap.get(date)!,regime=regimeMap.get(date)!;state=transitionStage21(state,{date,nextSessionDate:dates[index+1]??nextUsTradingSession(date),snap,regime,forceRebalance:date===PRODUCTION_PORTFOLIO.oosStartDate},maps);curve.push({date,equity:state.currentEquity,drawdown:state.drawdown})}
 const holdings=Object.entries(state.positions).map(([symbol,shares]):PortfolioHolding=>({symbol,entryPrice:state.entryPrices[symbol]??state.lastClose[symbol]??0,currentPrice:state.lastClose[symbol]??null,stopLevel:null,targetWeight:state.currentEquity>0?shares*(state.lastClose[symbol]??0)/state.currentEquity:0,role:symbol==="GLDM"?"DIVERSIFIER":"FIXED60"}));
 return{backtest:{strategyId:PRODUCTION_PORTFOLIO.strategyId,equityCurve:curve,stats:performanceStats(curve),benchmark:null,events:state.events},state,holdings};
}

export function buildStage21Portfolio(histories:Record<string,PricePoint[]>,universeHistory:UniverseMonth[],cftcRows:CftcPositionRow[]):{backtest:BacktestResult;portfolioState:PortfolioLiveState;innerState:LiveStrategyState}{
 if(!(histories.GLDM??[]).length)throw new Error("Stage21 requires GLDM history");
 const {snaps,state:innerState}=fixedSnapshots(histories,universeHistory);if(snaps.length<2)throw new Error("Stage21 fixed snapshots are empty");
 const base=snaps[0].equity||1,fixedCurve=snaps.map(snap=>({date:snap.date,equity:snap.equity/base,drawdown:0}));let peak=0;for(const point of fixedCurve){peak=Math.max(peak,point.equity);point.drawdown=point.equity/peak-1}
 const g=runBreakoutShadow(histories,universeHistory,START,snaps.at(-1)!.date),regimes=regimeRows(fixedCurve,g,histories.QQQ??[],cftcRows),simulation=simulateStage21(histories,snaps,regimes),backtest={...simulation.backtest,events:[...simulation.backtest.events,...innerState.events].sort((left,right)=>left.date.localeCompare(right.date)||left.type.localeCompare(right.type))};
 const latest=snaps.at(-1)!,regime=regimes.at(-1)!,targets=combinedTargets(regime.regime,latest.target),latestDate=latest.date,eligible=latestDate>=PRODUCTION_PORTFOLIO.oosStartDate,pending=simulation.state.pending;
 const rebalance=eligible&&pending?.executionDate!=null,executionDate=rebalance?pending.executionDate:null;
 const reason=!eligible?`Stage21 OOS starts ${PRODUCTION_PORTFOLIO.oosStartDate}`:pending?.reason??"Target unchanged";
 const fixedPositions=new Map(innerState.currentPositions.map(position=>[position.symbol,position]));
 const holdings=simulation.holdings.map(holding=>{const fixed=fixedPositions.get(holding.symbol);return fixed?{...holding,entryPrice:fixed.entryPrice,stopLevel:fixed.stopLevel}:holding});
 const portfolioState:PortfolioLiveState={strategyId:PRODUCTION_PORTFOLIO.strategyId,asOf:latestDate,regime:regime.regime,cftc:regime.cftc,m3:regime.m3,fixed60:{strategyId:PRODUCTION_STRATEGY.strategyId,riskState:innerState.state,symbols:latest.target.symbols,innerWeights:latest.target.weights},targets,holdings,nextAction:{type:rebalance?"REBALANCE_NEXT_OPEN":"HOLD",executionDate,targets,reason}};
 return{backtest,portfolioState,innerState};
}
