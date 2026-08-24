"use client";

import { ArrowsClockwiseIcon, CalendarDotsIcon, ChartLineUpIcon, DatabaseIcon, GaugeIcon, ShieldCheckIcon, TrendUpIcon, WalletIcon, WatchIcon } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DashboardPayload } from "@/lib/types";
import { WatchlistView } from "./watchlist-view";

type Tab = "overview" | "universe" | "ranking" | "portfolio" | "risk" | "backtest" | "watchlist" | "schedule";
const tabs = [
  ["overview", "概要", GaugeIcon], ["universe", "Dynamic Universe", DatabaseIcon], ["ranking", "Momentum順位", TrendUpIcon],
  ["portfolio", "ポートフォリオ", WalletIcon], ["risk", "リスク", ShieldCheckIcon], ["backtest", "バックテスト", ChartLineUpIcon],
  ["watchlist", "ウォッチリスト", WatchIcon], ["schedule", "運用スケジュール", CalendarDotsIcon],
] as const;
const number = new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 2 });
const pct = (value: number | null | undefined, digits = 1) => value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
const money = (value: number | null | undefined) => value == null ? "—" : `$${number.format(value)}`;
const date = (value: string | null | undefined) => value ? value.replaceAll("-", ".") : "—";

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return <div className="dynamic-metric"><span>{label}</span><strong className={tone ? `tone-${tone}` : ""}>{value}</strong></div>;
}
function Section({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return <section className="dynamic-card"><header><h2>{title}</h2>{action}</header>{children}</section>;
}
function StateBadge({ state }: { state: string }) {
  const good = state === "INVESTED" || state === "READY_NEXT_OPEN";
  return <span className={`state-badge ${good ? "good" : "cash"}`}>{state.replaceAll("_", " ")}</span>;
}

export function MomentumApp({ initialDashboard }: { initialDashboard: DashboardPayload }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [data, setData] = useState(initialDashboard);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  async function refresh() {
    setRefreshing(true);
    setRefreshMessage(null);
    try {
      const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
      const response = await fetch(`${base}/data/dashboard.json?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("配信済みデータを読み込めませんでした。");
      const body = await response.json() as { dashboard?: DashboardPayload };
      if (!body.dashboard) throw new Error("最新版のdashboardが見つかりませんでした。");
      setData(body.dashboard);
      setRefreshMessage(`GitHub Actions生成版を取得しました（${date(body.dashboard.generatedAt.slice(0, 10))}）。`);
      setRefreshVersion((value) => value + 1);
    } catch (error) { setRefreshMessage(error instanceof Error ? error.message : "最新データの取得に失敗しました。"); }
    finally { setRefreshing(false); }
  }
  const title = tabs.find(([key]) => key === tab)?.[1] ?? "概要";
  return <div className="app-shell dynamic-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><TrendUpIcon weight="bold" /></div><div><strong>Momentum</strong><span>Dynamic Console</span></div></div>
      <nav>{tabs.map(([key, label, Icon]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}><Icon size={18} /><span>{label}</span></button>)}</nav>
      <div className="sidebar-foot"><span>Production strategy</span><strong>{data.config.strategyId}</strong></div>
    </aside>
    <main>
      <div className="topbar"><div><span>Point-in-Time / next-open</span><strong>{title}</strong></div><button className="refresh-button" onClick={refresh} disabled={refreshing}><ArrowsClockwiseIcon className={refreshing ? "spin" : ""} size={20} />最新データを読込</button></div>
      <div className="dynamic-content">
        {data.warning && <div className="data-warning">{data.warning}</div>}
        {refreshMessage && <div className="refresh-message">{refreshMessage}</div>}
        {tab === "overview" && <Overview data={data} />}
        {tab === "universe" && <Universe data={data} />}
        {tab === "ranking" && <Ranking data={data} />}
        {tab === "portfolio" && <Portfolio data={data} />}
        {tab === "risk" && <Risk data={data} />}
        {tab === "backtest" && <Backtest data={data} />}
        {tab === "watchlist" && <><div className="research-only">Research / observation only — Production Universeへは追加されません。</div><WatchlistView refreshVersion={refreshVersion} /></>}
        {tab === "schedule" && <Schedule data={data} />}
      </div>
    </main>
  </div>;
}

function Overview({ data }: { data: DashboardPayload }) {
  const signal = data.currentSignal, state = data.liveState;
  return <div className="dynamic-stack">
    <Section title="Next Action" action={<StateBadge state={state.state} />}><div className="next-action"><div><span>次回注文</span><strong>{state.nextAction.type.replaceAll("_", " ")}</strong><p>{state.nextAction.reason}</p></div><div><span>注文予定日</span><strong>{date(state.nextAction.executionDate)}</strong></div><div><span>対象</span><strong>{state.nextAction.symbols.join(" / ") || "—"}</strong><p>{state.nextAction.targetWeights.map((weight) => pct(weight, 0)).join(" / ")}</p></div></div></Section>
    <div className="dynamic-metric-grid five"><Metric label="QQQ CLOSE" value={money(data.qqq.close)} /><Metric label="QQQ 10M MA" value={money(data.qqq.monthlyMa)} /><Metric label="QQQ 100DMA" value={money(data.qqq.dailySma)} /><Metric label="QQQ 20D" value={pct(data.qqq.momentum20d)} tone={(data.qqq.momentum20d ?? 0) > 0 ? "good" : "bad"} /><Metric label="RECOVERY" value={`${state.recoveryConsecutiveDays}/${data.config.recovery.confirmationDays}`} /></div>
    <div className="overview-two"><Section title="Current Top2"><Top2 signal={signal} /></Section><Section title="Dynamic Universe"><div className="universe-summary"><strong>{data.currentUniverse?.symbols.length ?? 0}</strong><span>/ {data.config.universe.size} stocks</span><p>as-of {date(data.currentUniverse?.asOf)}</p><div><b>追加</b> {data.currentUniverse?.added.join(", ") || "なし"}</div><div><b>除外</b> {data.currentUniverse?.removed.join(", ") || "なし"}</div></div></Section></div>
  </div>;
}
function Top2({ signal }: { signal: DashboardPayload["currentSignal"] }) {
  if (!signal?.selectedSymbols.length) return <div className="empty-state">新規Risk-On portfolioはありません。</div>;
  return <div className="top2-grid">{signal.selectedSymbols.map((symbol, index) => <div key={symbol}><span>TOP {index + 1}</span><strong>{symbol}</strong><b>{pct(signal.targetWeights[index], 0)}</b></div>)}<div className="allocation-evidence"><span>Allocation</span><strong>{signal.allocationMode}</strong><p>zGap {signal.zGap?.toFixed(3) ?? "—"} / threshold {signal.zGap == null ? "—" : "0.250"}</p></div></div>;
}
function Universe({ data }: { data: DashboardPayload }) {
  const universe = data.currentUniverse;
  return <div className="dynamic-stack"><div className="dynamic-metric-grid"><Metric label="SIZE" value={`${universe?.symbols.length ?? 0}`} /><Metric label="TARGET" value={`${data.config.universe.size}`} /><Metric label="AS-OF" value={date(universe?.asOf)} /><Metric label="SOURCE FILINGS" value={`${universe?.sourceFilings.length ?? 0}`} /></div><Section title="Point-in-Time Universe" action={<span className="section-note">SEC N-PORT breadth only</span>}><div className="table-scroll"><table className="dynamic-table"><thead><tr><th>Rank</th><th>Ticker</th><th>ETF count</th><th>Aggregate weight</th><th>Max weight</th><th>Recency weight</th><th>Universe score</th></tr></thead><tbody>{universe?.symbols.map((row) => <tr key={row.symbol}><td>{row.universeRank}</td><td><strong>{row.symbol}</strong></td><td>{row.etfCount}</td><td>{row.aggregateWeight.toFixed(2)}</td><td>{row.maxWeight.toFixed(2)}</td><td>{row.recencyWeight.toFixed(2)}</td><td>{row.universeScore.toFixed(3)}</td></tr>)}</tbody></table></div></Section></div>;
}
function Ranking({ data }: { data: DashboardPayload }) {
  return <Section title="0 / 20 / 80 Momentum Ranking" action={<span className="section-note">1Mはsurge判定のみ</span>}><div className="table-scroll"><table className="dynamic-table"><thead><tr><th>Rank</th><th>Ticker</th><th>1M surge</th><th>3M × 20%</th><th>6M × 80%</th><th>Score</th><th>vs QQQ</th><th>判定</th></tr></thead><tbody>{data.currentSignal?.candidates.map((row) => <tr key={row.symbol} className={row.eligible ? "" : "muted-row"}><td>{row.rank ?? "—"}</td><td><strong>{row.symbol}</strong></td><td>{pct(row.oneMonth)}</td><td>{pct(row.threeMonth)}</td><td>{pct(row.sixMonth)}</td><td>{pct(row.score)}</td><td>{pct(row.scoreSpread)}</td><td><span className={`eligibility ${row.eligible ? "yes" : "no"}`}>{row.eligible ? "Eligible" : row.exclusionReason}</span></td></tr>)}</tbody></table></div></Section>;
}
function Portfolio({ data }: { data: DashboardPayload }) {
  return <div className="dynamic-stack"><Section title="Target Portfolio"><Top2 signal={data.currentSignal} /></Section><Section title="Current Positions"><div className="table-scroll"><table className="dynamic-table"><thead><tr><th>Ticker</th><th>Target</th><th>Entry</th><th>Current</th><th>Since entry</th><th>Stop level</th></tr></thead><tbody>{data.liveState.currentPositions.map((position) => <tr key={position.symbol}><td><strong>{position.symbol}</strong></td><td>{pct(position.targetWeight, 0)}</td><td>{money(position.entryPrice)}</td><td>{money(position.currentPrice)}</td><td>{position.currentPrice ? pct(position.currentPrice / position.entryPrice - 1) : "—"}</td><td className="tone-bad">{money(position.stopLevel)}</td></tr>)}</tbody></table>{!data.liveState.currentPositions.length && <div className="empty-state">現在はCashです。</div>}</div></Section></div>;
}
function Risk({ data }: { data: DashboardPayload }) {
  const state = data.liveState;
  return <div className="dynamic-stack"><div className="dynamic-metric-grid"><Metric label="STATE" value={state.state} /><Metric label="PORTFOLIO PEAK" value={state.portfolioPeak.toFixed(3)} /><Metric label="CURRENT EQUITY" value={state.currentEquity.toFixed(3)} /><Metric label="DRAWDOWN" value={pct(state.drawdown)} tone="bad" /></div><Section title="Persistent Risk Control"><div className="rules-grid"><div><span>Individual stop</span><strong>-17.5%</strong><p>Close確認 → 翌営業日Openで全売却</p></div><div><span>Portfolio circuit</span><strong>-15.0%</strong><p>Peak比Close確認 → 翌営業日Openで全売却</p></div><div><span>Recovery</span><strong>10 closes</strong><p>10M gate + 100DMA + 20D momentum</p></div><div><span>Execution cost</span><strong>10 bp / side</strong><p>Entry・Exitの双方へ反映</p></div></div></Section><Section title="Last Trigger"><p className="trigger-text">{state.lastTrigger ?? "トリガー履歴はありません。"}</p></Section></div>;
}
function Backtest({ data }: { data: DashboardPayload }) {
  const stats = data.backtest.stats;
  const chart = useMemo(() => data.backtest.equityCurve.map((point, index) => ({ date: point.date, strategy: point.equity, benchmark: data.backtest.benchmark?.equityCurve[index]?.equity })), [data]);
  return <div className="dynamic-stack"><div className="dynamic-metric-grid five"><Metric label="FINAL EQUITY" value={`${stats.finalEquity.toFixed(2)}x`} /><Metric label="CAGR" value={pct(stats.cagr)} tone="good" /><Metric label="MAX DD" value={pct(stats.maxDrawdown)} tone="bad" /><Metric label="ANNUALIZED VOL" value={pct(stats.annualizedVolatility)} /><Metric label="CALMAR" value={stats.calmar?.toFixed(2) ?? "—"} /></div><Section title="Daily State-Machine Equity"><div className="equity-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><defs><linearGradient id="equity" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#167a4b" stopOpacity={0.3}/><stop offset="100%" stopColor="#167a4b" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#dce1da" vertical={false}/><XAxis dataKey="date" minTickGap={60}/><YAxis/><Tooltip/><Area type="monotone" dataKey="strategy" stroke="#167a4b" fill="url(#equity)" strokeWidth={2}/></AreaChart></ResponsiveContainer></div><p className="section-note">Benchmark: {data.backtest.benchmark?.label ?? "データなし"}</p></Section></div>;
}
function Schedule({ data }: { data: DashboardPayload }) {
  return <div className="overview-two"><Section title="MONTHLY — 米国月末Close後"><ol className="workflow"><li>公開済みN-PORTだけでUniverseをfreeze</li><li>0/20/80 MomentumとQQQ比較</li><li>Top2・zGap・50/50または70/30を確定</li><li>翌US trading session OPENでrebalance</li></ol></Section><Section title="DAILY — 米国Close後"><ol className="workflow"><li>-17.5% individual stopを判定</li><li>-15% portfolio circuitを判定</li><li>100DMA・20D momentum・回復連続日数を更新</li><li>必要な注文を翌US session OPENへ予約</li></ol></Section><Section title="Execution Contract"><div className="rules-grid"><div><span>Signal</span><strong>CLOSE</strong></div><div><span>Order</span><strong>NEXT OPEN</strong></div><div><span>One-way cost</span><strong>{pct(data.config.execution.transactionCost, 1)}</strong></div></div></Section></div>;
}
