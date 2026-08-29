"use client";

import { ArrowsClockwiseIcon, ChartLineUpIcon, ClockCounterClockwiseIcon, DatabaseIcon, GaugeIcon, GearIcon, TrendUpIcon, WalletIcon, XIcon } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { buildExpectedCagrOverlay } from "@/lib/expected-cagr";
import type { DashboardPayload, EquityPoint, ExpectedCagrModel, NextActionType, PerformanceStats } from "@/lib/types";
import nportDelayMonteCarlo from "../../data/research/nport-delay-monte-carlo.json";

type Tab = "overview" | "universe" | "ranking" | "portfolio" | "oos" | "backtest" | "schedule";
const tabs = [
  ["overview", "概要", GaugeIcon], ["universe", "Dynamic Universe", DatabaseIcon], ["ranking", "Momentum順位", TrendUpIcon],
  ["portfolio", "ポートフォリオ", WalletIcon], ["oos", "OOS", ChartLineUpIcon],
  ["backtest", "バックテスト", ClockCounterClockwiseIcon],
  ["schedule", "設定", GearIcon],
] as const;
const mobileTabLabels: Partial<Record<Tab, string>> = {
  portfolio: "保有",
  backtest: "検証",
  schedule: "設定",
};
const number = new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 2 });
const pct = (value: number | null | undefined, digits = 1) => value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
const money = (value: number | null | undefined) => value == null ? "—" : `$${number.format(value)}`;
const currentValue = (data: DashboardPayload, symbol: string, fallback: number | null | undefined) => data.latestPrices?.[symbol]?.price ?? fallback;
const date = (value: string | null | undefined) => value ? value.replaceAll("-", ".") : "—";
const updatedAt = (value: string) => {
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date(value));
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}.${part("month")}.${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
};
const usMarketOpenAt = (value: string | null | undefined) => {
  if (!value) return "—";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const targetWallClock = Date.UTC(year, month - 1, day, 9, 30);
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  let instant = new Date(targetWallClock);
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = formatter.formatToParts(instant);
    const part = (type: Intl.DateTimeFormatPartTypes) => Number(parts.find((item) => item.type === type)?.value ?? 0);
    const renderedWallClock = Date.UTC(part("year"), part("month") - 1, part("day"), part("hour"), part("minute"));
    instant = new Date(instant.getTime() + targetWallClock - renderedWallClock);
  }
  return updatedAt(instant.toISOString()).slice(0, 16);
};
const NEXT_ACTIONS: Array<{ type: NextActionType; meaning: string }> = [
  { type: "BUY_NEXT_OPEN", meaning: "次の米国営業日の寄付きでTop2を新規購入します。" },
  { type: "SELL_ALL_NEXT_OPEN", meaning: "次の米国営業日の寄付きで全保有銘柄を売却します。" },
  { type: "HOLD", meaning: "現在のポートフォリオをそのまま維持します。" },
  { type: "CASH_RECOVERY", meaning: "現金のまま、Recovery条件が10営業日連続で成立するまで待機します。" },
  { type: "MONTH_END_REBALANCE_NEXT_OPEN", meaning: "月末シグナル確定後、次の米国営業日の寄付きでTop2へリバランスします。" },
  { type: "CASH", meaning: "保留中の注文はなく、現金で待機します。" },
];

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return <div className="dynamic-metric"><span>{label}</span><strong className={tone ? `tone-${tone}` : ""}>{value}</strong></div>;
}
function Section({ title, action, children, onActivate }: { title: string; action?: React.ReactNode; children: React.ReactNode; onActivate?: () => void }) {
  return <section className={`dynamic-card${onActivate ? " interactive-card" : ""}`} role={onActivate ? "button" : undefined} tabIndex={onActivate ? 0 : undefined} aria-label={onActivate ? `${title}の説明を開く` : undefined} onClick={onActivate} onKeyDown={onActivate ? (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onActivate(); } } : undefined}><header><h2>{title}</h2>{action}</header>{children}</section>;
}
function StateBadge({ state }: { state: string }) {
  const good = state === "INVESTED" || state === "READY_NEXT_OPEN";
  return <span className={`state-badge ${good ? "good" : "cash"}`}>{state.replaceAll("_", " ")}</span>;
}

export function MomentumApp({ initialDashboard }: { initialDashboard: DashboardPayload }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [data, setData] = useState(initialDashboard);
  const [lastLoadedAt, setLastLoadedAt] = useState(initialDashboard.generatedAt);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  useEffect(() => {
    if (!refreshMessage) return;
    const timer = window.setTimeout(() => setRefreshMessage(null), 4_000);
    return () => window.clearTimeout(timer);
  }, [refreshMessage]);
  const loadLatest = useCallback(async (interactive: boolean) => {
    if (interactive) {
      setRefreshing(true);
      setRefreshMessage(null);
    }
    try {
      const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
      const response = await fetch(`${base}/data/dashboard.json?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("配信済みデータを読み込めませんでした。");
      const body = await response.json() as { dashboard?: DashboardPayload };
      if (!body.dashboard) throw new Error("最新版のdashboardが見つかりませんでした。");
      setData(body.dashboard);
      setLastLoadedAt(body.dashboard.generatedAt);
      if (interactive) setRefreshMessage(`GitHub Actions生成版を取得しました（${updatedAt(body.dashboard.generatedAt)}）。`);
    } catch (error) {
      if (interactive) setRefreshMessage(error instanceof Error ? error.message : "最新データの取得に失敗しました。");
    } finally {
      if (interactive) setRefreshing(false);
    }
  }, []);
  useEffect(() => {
    const poll = () => { void loadLatest(false); };
    const interval = window.setInterval(poll, 5 * 60 * 1_000);
    const refreshWhenVisible = () => { if (document.visibilityState === "visible") poll(); };
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [loadLatest]);
  const refresh = () => { void loadLatest(true); };
  const title = tabs.find(([key]) => key === tab)?.[1] ?? "概要";
  return <div className="app-shell dynamic-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><TrendUpIcon weight="bold" /></div><div><strong>Momentum</strong><span>Dynamic Console</span></div></div>
      <nav>{tabs.map(([key, label, Icon]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}><Icon size={18} /><span className="tab-label-default">{label}</span><span className="tab-label-mobile">{mobileTabLabels[key] ?? label}</span></button>)}</nav>
      <div className="sidebar-foot"><span>Production strategy</span><strong>{data.config.strategyId}</strong></div>
    </aside>
    <main>
      <div className="topbar"><div><span>Point-in-Time / next-open</span><strong>{title}</strong></div><div className="topbar-refresh"><span className="last-updated" title={`データ生成 ${updatedAt(data.generatedAt)}`}><b>最終更新</b> {updatedAt(lastLoadedAt)}</span><button className="refresh-button" onClick={refresh} disabled={refreshing}><ArrowsClockwiseIcon className={refreshing ? "spin" : ""} size={20} />最新データを読込</button></div></div>
      <div className="dynamic-content">
        {data.warning && <div className="data-warning">{data.warning}</div>}
        {refreshMessage && <div className="refresh-message">{refreshMessage}</div>}
        {tab === "overview" && <Overview data={data} />}
        {tab === "universe" && <Universe data={data} />}
        {tab === "ranking" && <Ranking data={data} />}
        {tab === "portfolio" && <Portfolio data={data} />}
        {tab === "oos" && <Oos data={data} />}
        {tab === "backtest" && <Backtest data={data} />}
        {tab === "schedule" && <Schedule data={data} />}
      </div>
    </main>
  </div>;
}

function Overview({ data }: { data: DashboardPayload }) {
  const [showActionGuide, setShowActionGuide] = useState(false);
  const signal = data.currentSignal, state = data.liveState;
  useEffect(() => {
    if (!showActionGuide) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setShowActionGuide(false); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [showActionGuide]);
  return <div className="dynamic-stack">
    <Section title="Next Action" action={<StateBadge state={state.state} />} onActivate={() => setShowActionGuide(true)}><div className="next-action"><div><span>次回注文</span><div className="next-action-copy"><strong>{state.nextAction.type.replaceAll("_", " ")}</strong><p>{state.nextAction.reason}</p></div></div><div><span>対象</span><div className="next-action-copy"><strong>{state.nextAction.symbols.join(" / ") || "—"}</strong><p>{state.nextAction.targetWeights.map((weight) => pct(weight, 0)).join(" / ")}</p></div></div><div><span>注文予定時刻</span><div className="next-action-copy"><strong>{usMarketOpenAt(state.nextAction.executionDate)}</strong></div></div><div><span>N-PORT取込期限</span><div className="next-action-copy"><strong>{data.nportOperations?.nextImportDeadlineAt ? updatedAt(data.nportOperations.nextImportDeadlineAt).slice(0, 16) : "—"}</strong>{data.nportOperations?.universeMode === "FALLBACK" && <p>旧Universeで継続</p>}</div></div></div></Section>
    <div className="dynamic-metric-grid five"><Metric label="QQQ 現在値" value={money(currentValue(data, "QQQ", data.qqq.close))} /><Metric label="QQQ 10M MA" value={money(data.qqq.monthlyMa)} /><Metric label="QQQ 100DMA" value={money(data.qqq.dailySma)} /><Metric label="QQQ 20D" value={pct(data.qqq.momentum20d)} tone={(data.qqq.momentum20d ?? 0) > 0 ? "good" : "bad"} /><Metric label="RECOVERY" value={`${state.recoveryConsecutiveDays}/${data.config.recovery.confirmationDays}`} /></div>
    <div className="overview-two"><Section title="Current Top2"><Top2 signal={signal} /></Section><Section title="Dynamic Universe"><div className="universe-summary"><strong>{data.currentUniverse?.symbols.length ?? 0}</strong><span>/ {data.config.universe.size} stocks</span><p>as-of {date(data.currentUniverse?.asOf)}</p><div><b>追加</b> {data.currentUniverse?.added.join(", ") || "なし"}</div><div><b>除外</b> {data.currentUniverse?.removed.join(", ") || "なし"}</div></div></Section></div>
    {showActionGuide && <div className="modal-backdrop" onMouseDown={() => setShowActionGuide(false)}><div className="action-modal" role="dialog" aria-modal="true" aria-labelledby="action-guide-title" onMouseDown={(event) => event.stopPropagation()}><header><div><span>NEXT ACTION GUIDE</span><h2 id="action-guide-title">6種類のアクション</h2></div><button type="button" aria-label="閉じる" onClick={() => setShowActionGuide(false)}><XIcon size={20} /></button></header><div className="action-guide-list">{NEXT_ACTIONS.map((item) => <div key={item.type} className={item.type === state.nextAction.type ? "current" : ""}><strong>{item.type.replaceAll("_", " ")}</strong><p>{item.meaning}</p>{item.type === state.nextAction.type && <span>現在</span>}</div>)}</div></div></div>}
  </div>;
}
function Top2({ signal }: { signal: DashboardPayload["currentSignal"] }) {
  if (!signal?.selectedSymbols.length) return <div className="empty-state">新規Risk-On portfolioはありません。</div>;
  return <div className="top2-grid">{signal.selectedSymbols.map((symbol, index) => <div key={symbol}><span>TOP {index + 1}</span><strong>{symbol}</strong><b>{pct(signal.targetWeights[index], 0)}</b></div>)}</div>;
}
function Universe({ data }: { data: DashboardPayload }) {
  const universe = data.currentUniverse;
  return <div className="dynamic-stack"><div className="dynamic-metric-grid two"><Metric label="TARGET" value={`${data.config.universe.size}`} /><Metric label="SOURCE FILINGS" value={`${universe?.sourceFilings.length ?? 0}`} /></div><Section title="Point-in-Time Universe" action={<div className="section-actions"><span className="section-asof">as-of {date(universe?.asOf)}</span><span className="section-note">SEC N-PORT breadth only</span></div>}><div className="table-scroll"><table className="dynamic-table"><thead><tr><th>Rank</th><th>Ticker</th><th>ETF count</th><th>Aggregate weight</th><th>Max weight</th><th>Recency weight</th><th>Universe score</th></tr></thead><tbody>{universe?.symbols.map((row) => <tr key={row.symbol}><td>{row.universeRank}</td><td><strong>{row.symbol}</strong></td><td>{row.etfCount}</td><td>{row.aggregateWeight.toFixed(2)}</td><td>{row.maxWeight.toFixed(2)}</td><td>{row.recencyWeight.toFixed(2)}</td><td>{row.universeScore.toFixed(3)}</td></tr>)}</tbody></table></div></Section></div>;
}
function Ranking({ data }: { data: DashboardPayload }) {
  return <Section title="0 / 20 / 80 Momentum Ranking" action={<div className="section-actions"><span className="section-asof">as-of {date(data.currentSignal?.signalDate)}</span><span className="section-note">1Mはsurge判定のみ</span></div>}><div className="table-scroll"><table className="dynamic-table"><thead><tr><th>Rank</th><th>Ticker</th><th>1M surge</th><th>3M × 20%</th><th>6M × 80%</th><th>Score</th><th>vs QQQ</th><th>判定</th></tr></thead><tbody>{data.currentSignal?.candidates.map((row) => <tr key={row.symbol} className={row.eligible ? "" : "muted-row"}><td>{row.rank ?? "—"}</td><td><strong>{row.symbol}</strong></td><td>{pct(row.oneMonth)}</td><td>{pct(row.threeMonth)}</td><td>{pct(row.sixMonth)}</td><td>{pct(row.score)}</td><td>{pct(row.scoreSpread)}</td><td><span className={`eligibility ${row.eligible ? "yes" : "no"}`}>{row.eligible ? "Eligible" : row.exclusionReason}</span></td></tr>)}</tbody></table></div></Section>;
}
function Portfolio({ data }: { data: DashboardPayload }) {
  return <div className="dynamic-stack"><Section title="Target Portfolio"><Top2 signal={data.currentSignal} /></Section><Section title="Current Positions"><div className="table-scroll"><table className="dynamic-table"><thead><tr><th>Ticker</th><th>Target</th><th>Entry</th><th>Current</th><th>Since entry</th><th>Stop level</th></tr></thead><tbody>{data.liveState.currentPositions.map((position) => { const current = currentValue(data, position.symbol, position.currentPrice); return <tr key={position.symbol}><td><strong>{position.symbol}</strong></td><td>{pct(position.targetWeight, 0)}</td><td>{money(position.entryPrice)}</td><td>{money(current)}</td><td>{current ? pct(current / position.entryPrice - 1) : "—"}</td><td className="tone-bad">{money(position.stopLevel)}</td></tr>; })}</tbody></table>{!data.liveState.currentPositions.length && <div className="empty-state">現在はCashです。</div>}</div></Section></div>;
}
function Backtest({ data }: { data: DashboardPayload }) {
  return <div className="dynamic-stack"><PerformanceView stats={data.backtest.stats} equityCurve={data.backtest.equityCurve} title="Daily State-Machine Equity" gradientId="backtest-equity" expectedCagr={data.expectedCagr} /><MonthlyReturnDistribution /></div>;
}
function Oos({ data }: { data: DashboardPayload }) {
  return <PerformanceView stats={data.oos.stats} equityCurve={data.oos.equityCurve} title="Forward OOS Equity" gradientId="oos-equity" />;
}
function PerformanceView({ stats, equityCurve, title, gradientId, expectedCagr }: { stats: PerformanceStats; equityCurve: EquityPoint[]; title: string; gradientId: string; expectedCagr?: ExpectedCagrModel }) {
  const chart = useMemo(() => expectedCagr ? buildExpectedCagrOverlay(equityCurve, expectedCagr) : equityCurve.map((point) => ({ date: point.date, strategy: point.equity })), [equityCurve, expectedCagr]);
  return <div className="dynamic-stack"><div className="dynamic-metric-grid five"><Metric label="FINAL EQUITY" value={`${stats.finalEquity.toFixed(2)}x`} /><Metric label="CAGR" value={pct(stats.cagr)} tone="good" /><Metric label="MAX DD" value={pct(stats.maxDrawdown)} tone="bad" /><Metric label="ANNUALIZED VOL" value={pct(stats.annualizedVolatility)} /><Metric label="CALMAR" value={stats.calmar?.toFixed(2) ?? "—"} /></div><Section title={title} action={expectedCagr ? <span className="section-asof">Monte Carlo as-of {date(expectedCagr.sample.end)}</span> : undefined}><div className="equity-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><defs><linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#167a4b" stopOpacity={0.3}/><stop offset="100%" stopColor="#167a4b" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#dce1da" vertical={false}/><XAxis dataKey="date" minTickGap={60}/><YAxis scale="log" domain={["auto", "auto"]} allowDataOverflow tickFormatter={(value) => `${Number(value).toFixed(Number(value) < 10 ? 1 : 0)}x`}/><Tooltip formatter={(value) => Array.isArray(value) ? value.map((item) => `${Number(item).toFixed(3)}x`).join(" – ") : `${Number(value).toFixed(3)}x`}/><Legend verticalAlign="top" height={38}/>{expectedCagr && <><Area name="Central 90%" type="monotone" dataKey="central90" stroke="none" fill="#bfcac2" fillOpacity={0.34} isAnimationActive={false}/><Area name="Central 50%" type="monotone" dataKey="central50" stroke="none" fill="#78aa8a" fillOpacity={0.42} isAnimationActive={false}/><Line name="Expected CAGR" type="monotone" dataKey="expected" stroke="#52745f" strokeDasharray="6 5" strokeWidth={1.5} dot={false} isAnimationActive={false}/></>}<Area name="Backtest" type="monotone" dataKey="strategy" stroke="#167a4b" fill={`url(#${gradientId})`} strokeWidth={2} isAnimationActive animationDuration={1_000}/></AreaChart></ResponsiveContainer></div>{expectedCagr && <div className="monte-carlo-note"><span>Central 50% {pct(expectedCagr.estimate.central50[0])}–{pct(expectedCagr.estimate.central50[1])}</span><span>Central 90% {pct(expectedCagr.estimate.central90[0])}–{pct(expectedCagr.estimate.central90[1])}</span><p>CAGRのブートストラップ区間を複利換算した参考帯です。将来価格の予測帯ではありません。</p></div>}</Section></div>;
}
function MonthlyReturnDistribution() {
  const monthlyReturns = nportDelayMonteCarlo.monteCarlo.monthlyReturns;
  return <Section title="月別リターン分布" action={<span className="section-asof">N-PORT delay Monte Carlo · {number.format(nportDelayMonteCarlo.paths)} paths</span>}><div className="monthly-return-distribution"><ResponsiveContainer width="100%" height="100%"><BarChart data={monthlyReturns.histogram5Pct} margin={{ top: 10, right: 8, bottom: 8, left: 0 }}><CartesianGrid stroke="#dce1da" vertical={false}/><XAxis dataKey="label" interval={0} height={42} tick={{ fontSize: 10 }} tickFormatter={(label) => { const tick = String(label).split("%")[0]; return tick === "-0" ? "0" : tick; }}/><YAxis width={46} tickFormatter={(value) => `${(Number(value) * 100).toFixed(0)}%`}/><Tooltip cursor={{ fill: "#f0f2ee" }} formatter={(value) => [`${(Number(value) * 100).toFixed(2)}%`, "発生確率"]} labelFormatter={(label) => `月次リターン ${label}`}/><Bar dataKey="probability" name="発生確率" isAnimationActive animationDuration={1_000}>{monthlyReturns.histogram5Pct.map((bin) => <Cell key={bin.label} fill={bin.to <= 0 ? "#c43b31" : bin.from >= 0.049 ? "#167a4b" : "#73776f"}/>)}</Bar></BarChart></ResponsiveContainer></div><div className="monthly-return-summary"><span>マイナス月 <strong>{pct(monthlyReturns.negativeProbability, 2)}</strong></span><span>0%月 <strong>{pct(monthlyReturns.zeroProbability, 2)}</strong></span><span>プラス月 <strong>{pct(monthlyReturns.positiveProbability, 2)}</strong></span></div></Section>;
}
function Schedule({ data }: { data: DashboardPayload }) {
  return <div className="dynamic-stack"><div className="overview-two"><Section title="MONTHLY — 米国月末Close後"><ol className="workflow"><li>公開済みN-PORTだけでUniverseをfreeze</li><li>0/20/80 MomentumとQQQ比較</li><li>Top2・zGap・50/50または70/30を確定</li></ol></Section><Section title="DAILY — 米国Close後"><ol className="workflow"><li>-17.5% individual stopを判定</li><li>-15% portfolio circuitを判定</li><li>100DMA・20D momentum・回復連続日数を更新</li></ol></Section><Section title="Execution Contract"><div className="rules-grid execution-grid"><div><span>Signal</span><strong>CLOSE</strong></div><div><span>Order</span><strong>NEXT OPEN</strong></div><div><span>One-way cost</span><strong>{pct(data.config.execution.transactionCost, 1)}</strong></div></div></Section></div><Section title="Persistent Risk Control"><div className="rules-grid"><div><span>Individual stop</span><strong>-17.5%</strong></div><div><span>Portfolio circuit</span><strong>-15.0%</strong></div><div><span>Recovery</span><strong>10 closes</strong></div><div><span>Execution cost</span><strong className="execution-cost">10 bp</strong></div></div></Section><Section title="Last Trigger"><p className="trigger-text">{data.liveState.lastTrigger ?? "トリガー履歴はありません。"}</p></Section></div>;
}
