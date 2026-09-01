"use client";

import { ArrowsClockwiseIcon, ChartLineUpIcon, ClockCounterClockwiseIcon, DatabaseIcon, GaugeIcon, GearIcon, TrendUpIcon, WalletIcon } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { evaluateOosActionGate } from "@/lib/oos-action-gate";
import type { DashboardPayload, EquityPoint } from "@/lib/types";
import type { PortfolioTarget } from "@/lib/portfolio-types";

type Tab="overview"|"universe"|"ranking"|"portfolio"|"oos"|"backtest"|"schedule";
const tabs=[["overview","概要",GaugeIcon],["universe","Dynamic Universe",DatabaseIcon],["ranking","Momentum順位",TrendUpIcon],["portfolio","ポートフォリオ",WalletIcon],["oos","OOS",ChartLineUpIcon],["backtest","バックテスト",ClockCounterClockwiseIcon],["schedule","設定",GearIcon]] as const;
const pct=(v:number|null|undefined,d=1)=>v==null?"—":`${(v*100).toFixed(d)}%`;
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
export function MomentumApp({initialDashboard}:{initialDashboard:DashboardPayload}){
 const[tab,setTab]=useState<Tab>("overview"),[data,setData]=useState(initialDashboard),[refreshing,setRefreshing]=useState(false);
 const loadLatest=useCallback(async()=>{setRefreshing(true);try{const base=process.env.NEXT_PUBLIC_BASE_PATH??"";const r=await fetch(`${base}/data/dashboard.json?t=${Date.now()}`,{cache:"no-store"});const b=await r.json() as {dashboard:DashboardPayload};setData(b.dashboard)}finally{setRefreshing(false)}},[]);
 useEffect(()=>{const id=window.setInterval(()=>void loadLatest(),5*60*1000);return()=>window.clearInterval(id)},[loadLatest]);
 return <div className="app-shell dynamic-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark"><TrendUpIcon weight="bold"/></div><div><strong>Momentum</strong><span>Stage21 Console</span></div></div><nav>{tabs.map(([k,l,I])=><button key={k} className={tab===k?"active":""} onClick={()=>setTab(k)}><I size={18}/><span>{l}</span></button>)}</nav><div className="sidebar-foot"><span>Production</span><strong>{data.portfolioConfig.strategyId}</strong></div></aside><main><div className="topbar"><div><span>Point-in-Time / next-open</span><strong>{tabs.find(([k])=>k===tab)?.[1]}</strong></div><button className="refresh-button" onClick={()=>void loadLatest()} disabled={refreshing}><ArrowsClockwiseIcon className={refreshing?"spin":""} size={20}/>最新データを読込</button></div><div className="dynamic-content">{data.warning&&<div className="data-warning">{data.warning}</div>}{tab==="overview"&&<Overview data={data}/>} {tab==="universe"&&<Universe data={data}/>} {tab==="ranking"&&<Ranking data={data}/>} {tab==="portfolio"&&<Portfolio data={data}/>} {tab==="oos"&&<Oos data={data}/>} {tab==="backtest"&&<Backtest data={data}/>} {tab==="schedule"&&<Schedule data={data}/>}</div></main></div>
}
function Overview({data}:{data:DashboardPayload}){
 const p=data.portfolioState,gate=evaluateOosActionGate(data.oos),act=p.nextAction;
 const actionLabel=act.type==="REBALANCE_NEXT_OPEN"?"リバランス":act.type==="HOLD"?"維持":"確認";
 return <div className="dynamic-stack">
  <Section title="次に取る投資行動"><div className="next-action" style={{gridTemplateColumns:"repeat(4,minmax(0,1fr))"}}>
   <div><span>行動</span><div className="next-action-copy"><strong>{actionLabel}</strong><p>{act.reason}</p></div></div>
   <div><span>実行時刻（日本時間）</span><div className="next-action-copy"><strong>{act.executionDate?usOpenJst(act.executionDate):"注文なし"}</strong><p>{act.executionDate?`${act.executionDate} 米国寄付き`:"現在の配分を維持"}</p></div></div>
   <div style={{gridColumn:"span 2"}}><span>目標配分</span><div className="next-action-copy"><strong>{targetText(act.targets)}</strong><p>合計100% / 借入・証拠金なし</p></div></div>
  </div></Section>
  <div className="dynamic-metric-grid five"><Metric label="Regime" value={p.regime}/><Metric label="CFTC" value={p.cftc.yellow?"YELLOW":"CLEAR"}/><Metric label="M3 Deep" value={p.m3.deep?"ON":"OFF"}/><Metric label="Inner Fixed60" value={p.fixed60.riskState}/><Metric label="OOS Gate" value={gate.level}/></div>
  <Section title="現在のProduction配分"><div className="allocation-list">{p.targets.map(t=><div key={`${t.symbol}-${t.role}`} className="allocation-row"><strong>{t.symbol}</strong><span>{t.role}</span><b>{pct(t.weight,1)}</b></div>)}</div></Section>
  <Section title="Fixed60 内部Top2"><p>{p.fixed60.symbols.length?p.fixed60.symbols.map((s,i)=>`${s} ${pct(p.fixed60.innerWeights[i],0)}`).join(" / "):"現在は内部Top2保有なし"}</p><small>これはStage21全体の最終配分ではありません。実際の売買は最上段の「次に取る投資行動」に従います。</small></Section>
 </div>
}
function Universe({data}:{data:DashboardPayload}){return <Section title="Dynamic Universe"><div className="simple-table">{(data.currentUniverse?.symbols??[]).map(x=><div key={x.symbol}><b>{x.universeRank}</b><strong>{x.symbol}</strong><span>ETF {x.etfCount}</span><span>Score {x.universeScore.toFixed(2)}</span></div>)}</div></Section>}
function Ranking({data}:{data:DashboardPayload}){return <Section title="Momentum順位"><div className="simple-table">{(data.currentSignal?.candidates??[]).filter(x=>x.rank).slice(0,20).map(x=><div key={x.symbol}><b>{x.rank}</b><strong>{x.symbol}</strong><span>{pct(x.threeMonth)}</span><span>{pct(x.sixMonth)}</span><span>{x.eligible?"eligible":x.exclusionReason}</span></div>)}</div></Section>}
function Portfolio({data}:{data:DashboardPayload}){const p=data.portfolioState;return <div className="dynamic-stack"><Section title="Production target"><div className="allocation-list">{p.targets.map(t=><div className="allocation-row" key={t.symbol}><strong>{t.symbol}</strong><span>{t.role}</span><b>{pct(t.weight,1)}</b></div>)}</div></Section><Section title="Regime inputs"><div className="dynamic-metric-grid"><Metric label="Regime" value={p.regime}/><Metric label="CFTC report" value={p.cftc.reportDate??"—"}/><Metric label="CFTC net" value={p.cftc.net==null?"—":Math.round(p.cftc.net).toLocaleString()}/><Metric label="4週前" value={p.cftc.priorNet==null?"—":Math.round(p.cftc.priorNet).toLocaleString()}/><Metric label="M3 gap" value={pct(p.m3.gap)}/></div></Section></div>}
function Oos({data}:{data:DashboardPayload}){const g=evaluateOosActionGate(data.oos);return <div className="dynamic-stack"><Section title="True Forward OOS"><div className="dynamic-metric-grid"><Metric label="開始" value={data.oos.startedAt}/><Metric label="As of" value={data.oos.asOf??"—"}/><Metric label="CAGR" value={pct(data.oos.stats.cagr)}/><Metric label="MaxDD" value={pct(data.oos.stats.maxDrawdown)}/><Metric label="Gate" value={g.level}/></div><p>{g.instruction}</p><small>{g.reason}</small></Section></div>}
function Backtest({data}:{data:DashboardPayload}){const curve=data.backtest.equityCurve,ref=data.portfolioConfig.researchReference;const chart=useMemo(()=>curve.map((x:EquityPoint)=>({date:x.date,equity:x.equity})),[curve]);return <div className="dynamic-stack"><div className="dynamic-metric-grid"><Metric label="Historical CAGR" value={pct(data.backtest.stats.cagr)}/><Metric label="Historical MaxDD" value={pct(data.backtest.stats.maxDrawdown)}/><Metric label="Planning proxy" value={pct(ref.planningCagrProxy)}/><Metric label="Rolling36 median" value={pct(ref.rolling36MedianCagr)}/><Metric label="Rolling36 worst" value={pct(ref.rolling36WorstCagr)}/></div><Section title="Stage21 equity"><div style={{height:360}}><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date" minTickGap={40}/><YAxis/><Tooltip/><Area type="monotone" dataKey="equity" stroke="currentColor" fill="currentColor" fillOpacity={0.12}/></AreaChart></ResponsiveContainer></div></Section><p>Planning proxyは同一sample内のstress/rolling検証から作った運用計画用proxyで、True Forward予測値ではありません。</p></div>}
function Schedule({data}:{data:DashboardPayload}){return <div className="dynamic-stack"><Section title="運用仕様"><div className="simple-table"><div><strong>Production ID</strong><span>{data.portfolioConfig.strategyId}</span></div><div><strong>OOS開始</strong><span>{data.portfolioConfig.oosStartDate}</span></div><div><strong>執行</strong><span>close確認 → next US open</span></div><div><strong>コスト</strong><span>{pct(data.portfolioConfig.execution.transactionCost,2)} / side</span></div><div><strong>N-PORT期限</strong><span>{data.nportOperations?.nextImportDeadlineAt?updatedAt(data.nportOperations.nextImportDeadlineAt):"—"}</span></div></div></Section></div>}
