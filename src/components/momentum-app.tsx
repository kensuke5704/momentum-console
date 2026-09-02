"use client";

import { ArrowsClockwiseIcon, ChartLineUpIcon, ClockCounterClockwiseIcon, DatabaseIcon, GaugeIcon, GearIcon, TrendUpIcon, WalletIcon } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { evaluateOosActionGate } from "@/lib/oos-action-gate";
import type { DashboardPayload, EquityPoint } from "@/lib/types";
import type { PortfolioTarget } from "@/lib/portfolio-types";

type Tab="overview"|"universe"|"ranking"|"portfolio"|"oos"|"backtest"|"schedule";
const tabs=[["overview","Overview",GaugeIcon],["universe","Universe",DatabaseIcon],["ranking","Ranking",TrendUpIcon],["portfolio","Portfolio",WalletIcon],["oos","OOS",ChartLineUpIcon],["backtest","Backtest",ClockCounterClockwiseIcon],["schedule","Settings",GearIcon]] as const;
const pct=(v:number|null|undefined,d=1)=>v==null?"—":`${(v*100).toFixed(d)}%`;
const equityTick=(value:number)=>value>=100?value.toFixed(0):value>=10?value.toFixed(1):value.toFixed(2);
const updatedAt=(value:string)=>new Intl.DateTimeFormat("ja-JP",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false}).format(new Date(value));
const usOpenJst=(date:string|null)=>{
 if(!date)return "—";
 const [y,m,d]=date.split("-").map(Number);const probe=new Date(Date.UTC(y,m-1,d,14,30));
 const nyHour=Number(new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",hour:"2-digit",hour12:false}).format(probe));
 const utcHour=nyHour===10?13:14;return updatedAt(new Date(Date.UTC(y,m-1,d,utcHour,30)).toISOString());
};
const targetText=(targets:PortfolioTarget[])=>targets.map(t=>`${t.symbol} ${pct(t.weight,1)}`).join(" / ")||"—";
function Metric({label,value}:{label:string;value:string}){return <div className="dynamic-metric"><span>{label}</span><strong>{value}</strong></div>}
function Section({title,children}:{title:string;children:React.ReactNode}){return <section className="dynamic-card"><header><h2>{title}</h2></header>{children}</section>}
function EquityChart({curve}:{curve:EquityPoint[]}){
 const chart=useMemo(()=>curve.filter(point=>point.equity>0).map(point=>({date:point.date,equity:point.equity})),[curve]);
 const domain=useMemo<[number,number]>(()=>{if(!chart.length)return[0.98,1.02];const values=chart.map(point=>point.equity),min=Math.min(...values),max=Math.max(...values);return[min/1.02,max*1.02]},[chart]);
 if(!chart.length)return <p className="page-note">No OOS equity data yet.</p>;
 return <div className="stage21-equity-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><CartesianGrid stroke="#dce1da" vertical={false}/><XAxis dataKey="date" minTickGap={40}/><YAxis scale="log" domain={domain} allowDataOverflow tickFormatter={equityTick}/><Tooltip formatter={(value)=>[equityTick(Number(value)),"Equity"]}/><Area type="monotone" dataKey="equity" stroke="#246b38" fill="#246b38" fillOpacity={0.12} isAnimationActive={false}/></AreaChart></ResponsiveContainer></div>
}
export function MomentumApp({initialDashboard}:{initialDashboard:DashboardPayload}){
 const[tab,setTab]=useState<Tab>("overview"),[data,setData]=useState(initialDashboard),[refreshing,setRefreshing]=useState(false);
 const loadLatest=useCallback(async()=>{setRefreshing(true);try{const base=process.env.NEXT_PUBLIC_BASE_PATH??"";const r=await fetch(`${base}/data/dashboard.json?t=${Date.now()}`,{cache:"no-store"});if(!r.ok)throw new Error(`Dashboard refresh failed: ${r.status}`);const b=await r.json() as {dashboard?:DashboardPayload};if(b.dashboard?.portfolioConfig?.strategyId&&b.dashboard?.portfolioState?.strategyId)setData(b.dashboard)}finally{setRefreshing(false)}},[]);
 useEffect(()=>{const id=window.setInterval(()=>void loadLatest(),60*1000);return()=>window.clearInterval(id)},[loadLatest]);
 return <div className="app-shell dynamic-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark"><TrendUpIcon weight="bold"/></div><div><strong>Momentum</strong><span>Stage21 Console</span></div></div><nav>{tabs.map(([k,l,I])=><button key={k} className={tab===k?"active":""} onClick={()=>setTab(k)}><I size={18}/><span>{l}</span></button>)}</nav><div className="sidebar-foot"><span>Production</span><strong>{data.portfolioConfig.strategyId}</strong></div></aside><main><div className="topbar"><div><span>Point-in-Time / next-open</span><strong>{tabs.find(([k])=>k===tab)?.[1]}</strong></div><button className="refresh-button" onClick={()=>void loadLatest()} disabled={refreshing}><ArrowsClockwiseIcon className={refreshing?"spin":""} size={20}/>Refresh</button></div><div className="dynamic-content">{data.warning&&<div className="data-warning">{data.warning}</div>}{tab==="overview"&&<Overview data={data}/>} {tab==="universe"&&<Universe data={data}/>} {tab==="ranking"&&<Ranking data={data}/>} {tab==="portfolio"&&<Portfolio data={data}/>} {tab==="oos"&&<Oos data={data}/>} {tab==="backtest"&&<Backtest data={data}/>} {tab==="schedule"&&<Schedule data={data}/>}</div></main></div>
}
function Overview({data}:{data:DashboardPayload}){
 const p=data.portfolioState,gate=evaluateOosActionGate(data.oos),act=p.nextAction;
 const actionLabel=act.type==="REBALANCE_NEXT_OPEN"?"REBALANCE":act.type==="HOLD"?"HOLD":"REVIEW";
 return <div className="dynamic-stack">
  <Section title="Next Action"><div className="next-action next-action-stage21">
   <div><span>Action</span><div className="next-action-copy"><strong>{actionLabel}</strong><p>{act.reason}</p></div></div>
   <div><span>Execution (JST)</span><div className="next-action-copy"><strong>{act.executionDate?usOpenJst(act.executionDate):"NO ORDER"}</strong><p>{act.executionDate?`${act.executionDate} US open`:"Keep allocation"}</p></div></div>
   <div className="target-cell"><span>Target</span><div className="next-action-copy"><strong>{targetText(act.targets)}</strong><p>100% total · no leverage</p></div></div>
  </div></Section>
  <div className="dynamic-metric-grid five"><Metric label="Regime" value={p.regime}/><Metric label="CFTC" value={p.cftc.yellow?"YELLOW":"CLEAR"}/><Metric label="M3 Deep" value={p.m3.deep?"ON":"OFF"}/><Metric label="Inner Fixed60" value={p.fixed60.riskState}/><Metric label="OOS Gate" value={gate.level}/></div>
  <Section title="Current Allocation"><div className="allocation-list">{p.targets.map(t=><div key={`${t.symbol}-${t.role}`} className="allocation-row"><strong>{t.symbol}</strong><span>{t.role}</span><b>{pct(t.weight,1)}</b></div>)}</div></Section>
  <Section title="Fixed60 Top2"><p>{p.fixed60.symbols.length?p.fixed60.symbols.map((s,i)=>`${s} ${pct(p.fixed60.innerWeights[i],0)}`).join(" / "):"No holdings"}</p></Section>
 </div>
}
function Universe({data}:{data:DashboardPayload}){return <Section title="Dynamic Universe"><div className="table-scroll"><table className="dynamic-table compact-table"><thead><tr><th>Rank</th><th>Ticker</th><th>ETF Count</th><th>Score</th></tr></thead><tbody>{(data.currentUniverse?.symbols??[]).map(x=><tr key={x.symbol}><td>{x.universeRank}</td><td><strong>{x.symbol}</strong></td><td>{x.etfCount}</td><td>{x.universeScore.toFixed(2)}</td></tr>)}</tbody></table></div></Section>}
function Ranking({data}:{data:DashboardPayload}){return <Section title="Momentum Ranking"><div className="table-scroll"><table className="dynamic-table compact-table"><thead><tr><th>Rank</th><th>Ticker</th><th>3M</th><th>6M</th><th>Status</th></tr></thead><tbody>{(data.currentSignal?.candidates??[]).filter(x=>x.rank).slice(0,20).map(x=><tr key={x.symbol}><td>{x.rank}</td><td><strong>{x.symbol}</strong></td><td>{pct(x.threeMonth)}</td><td>{pct(x.sixMonth)}</td><td>{x.eligible?"ELIGIBLE":x.exclusionReason}</td></tr>)}</tbody></table></div></Section>}
function Portfolio({data}:{data:DashboardPayload}){const p=data.portfolioState;return <div className="dynamic-stack"><Section title="Production Target"><div className="allocation-list">{p.targets.map(t=><div className="allocation-row" key={t.symbol}><strong>{t.symbol}</strong><span>{t.role}</span><b>{pct(t.weight,1)}</b></div>)}</div></Section><Section title="Regime Inputs"><div className="dynamic-metric-grid five"><Metric label="Regime" value={p.regime}/><Metric label="CFTC Used (PIT)" value={p.cftc.reportDate??"—"}/><Metric label="CFTC Net" value={p.cftc.net==null?"—":Math.round(p.cftc.net).toLocaleString()}/><Metric label="Prior 4W" value={p.cftc.priorNet==null?"—":Math.round(p.cftc.priorNet).toLocaleString()}/><Metric label="M3 Gap" value={pct(p.m3.gap)}/></div><p className="page-note">CFTC date is the latest report eligible for the Stage21 PIT decision, not the source feed&apos;s latest report.</p></Section></div>}
function Oos({data}:{data:DashboardPayload}){const g=evaluateOosActionGate(data.oos);return <div className="dynamic-stack"><Section title="Forward OOS"><div className="dynamic-metric-grid five"><Metric label="Start" value={data.oos.startedAt}/><Metric label="As of" value={data.oos.asOf??"—"}/><Metric label="CAGR" value={pct(data.oos.stats.cagr)}/><Metric label="MaxDD" value={pct(data.oos.stats.maxDrawdown)}/><Metric label="Gate" value={g.level}/></div></Section><Section title="OOS Equity · Log Scale"><EquityChart curve={data.oos.equityCurve}/></Section><p className="page-note">Validated OOS data · dashboard refreshes automatically every minute · updated {data.generatedAt?updatedAt(data.generatedAt):"—"}</p></div>}
function Backtest({data}:{data:DashboardPayload}){const ref=data.portfolioConfig.researchReference;return <div className="dynamic-stack"><div className="dynamic-metric-grid five"><Metric label="Historical CAGR" value={pct(data.backtest.stats.cagr)}/><Metric label="Historical MaxDD" value={pct(data.backtest.stats.maxDrawdown)}/><Metric label="Planning Proxy" value={pct(ref.planningCagrProxy)}/><Metric label="Rolling36 Median" value={pct(ref.rolling36MedianCagr)}/><Metric label="Rolling36 Worst" value={pct(ref.rolling36WorstCagr)}/></div><Section title="Stage21 Equity · Log Scale"><EquityChart curve={data.backtest.equityCurve}/></Section><p className="page-note">Planning proxy is not a forward forecast.</p></div>}
function Schedule({data}:{data:DashboardPayload}){return <div className="dynamic-stack"><Section title="Configuration"><div className="simple-table"><div><strong>Production ID</strong><span>{data.portfolioConfig.strategyId}</span></div><div><strong>OOS Start</strong><span>{data.portfolioConfig.oosStartDate}</span></div><div><strong>Execution</strong><span>Close confirmation → next US open</span></div><div><strong>Cost</strong><span>{pct(data.portfolioConfig.execution.transactionCost,2)} / side</span></div><div><strong>N-PORT Deadline</strong><span>{data.nportOperations?.nextImportDeadlineAt?updatedAt(data.nportOperations.nextImportDeadlineAt):"—"}</span></div></div></Section></div>}
