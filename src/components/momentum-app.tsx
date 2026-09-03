"use client";

import {
  ArrowsClockwiseIcon,
  CaretDownIcon,
  CaretUpDownIcon,
  CaretUpIcon,
  ChartLineUpIcon,
  ClockCounterClockwiseIcon,
  DatabaseIcon,
  GaugeIcon,
  GearIcon,
  TrendUpIcon,
  WalletIcon,
  XIcon,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { contrastingTextColor } from "@/lib/color-contrast";
import { latestCompletedUsTradingSession } from "@/lib/latest-session";
import { evaluateOosActionGate } from "@/lib/oos-action-gate";
import type { PortfolioTarget } from "@/lib/portfolio-types";
import type { DashboardPayload, EquityPoint, MomentumCandidate, UniverseMember } from "@/lib/types";

type Tab = "overview" | "universe" | "portfolio" | "oos" | "backtest" | "schedule";
type DetailKey = "regime" | "action" | "execution" | "nport" | "target" | "cftc" | "m3" | "fixed60" | "oos";
type SortDirection = "asc" | "desc";
type CombinedSortKey =
  | "universeRank"
  | "symbol"
  | "etfCount"
  | "universeScore"
  | "momentumRank"
  | "threeMonth"
  | "sixMonth"
  | "score"
  | "status";

type CombinedRow = UniverseMember & {
  candidate: MomentumCandidate | null;
  momentumRank: number | null;
  status: string;
};

const tabs = [
  ["overview", "Overview", GaugeIcon],
  ["universe", "Universe", DatabaseIcon],
  ["portfolio", "Portfolio", WalletIcon],
  ["oos", "OOS", ChartLineUpIcon],
  ["backtest", "Backtest", ClockCounterClockwiseIcon],
  ["schedule", "Settings", GearIcon],
] as const;

const pct = (value: number | null | undefined, digits = 1) =>
  value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
const equityTick = (value: number) => value >= 100 ? value.toFixed(0) : value >= 10 ? value.toFixed(1) : value.toFixed(2);

const dateLabel = (value: string | null | undefined) => {
  if (!value) return "—";
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1].slice(-2)}/${match[2]}/${match[3]}` : value;
};

const updatedAt = (value: string) => {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(value)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return `${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}`;
};

const usOpenJst = (date: string | null) => {
  if (!date) return "—";
  const [year, month, day] = date.split("-").map(Number);
  const probe = new Date(Date.UTC(year, month - 1, day, 14, 30));
  const nyHour = Number(new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "2-digit",
    hour12: false,
  }).format(probe));
  const utcHour = nyHour === 10 ? 13 : 14;
  return updatedAt(new Date(Date.UTC(year, month - 1, day, utcHour, 30)).toISOString());
};

const usCloseJst = (date: string) => {
  const [year, month, day] = date.split("-").map(Number);
  const probe = new Date(Date.UTC(year, month - 1, day, 20));
  const nyHour = Number(new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "2-digit",
    hour12: false,
  }).format(probe));
  const utcHour = nyHour === 16 ? 20 : 21;
  return updatedAt(new Date(Date.UTC(year, month - 1, day, utcHour)).toISOString());
};

const targetText = (targets: PortfolioTarget[]) =>
  targets.map((target) => `${target.symbol} ${pct(target.weight, 1)}`).join(" / ") || "—";

function Metric({ label, value, nowrap = false }: { label: string; value: string; nowrap?: boolean }) {
  const density = value.length > 16 ? " metric-value-dense" : value.length > 10 ? " metric-value-compact" : "";
  return <div className={`dynamic-metric${nowrap ? " metric-nowrap" : ""}`}><span>{label}</span><strong className={density.trim()} title={value}>{value}</strong></div>;
}

function StatusMetric({ label, value, onClick }: { label: string; value: string; onClick: () => void }) {
  return <button type="button" className="dynamic-metric interactive-metric" onClick={onClick} aria-label={`${label} details`}>
    <span>{label}</span><strong>{value}</strong>
  </button>;
}

type DefinitionItem = { name: string; meaning: string };

function DefinitionList({ current, items }: { current: string; items: DefinitionItem[] }) {
  return <div className="detail-definitions">
    {items.map((item) => <div className={`detail-definition${item.name === current ? " current" : ""}`} key={item.name}>
      <div><strong>{item.name}</strong>{item.name === current && <span>CURRENT</span>}</div>
      <p>{item.meaning}</p>
    </div>)}
  </div>;
}

function Section({ title, children, className = "", asOf }: { title: string; children: React.ReactNode; className?: string; asOf?: string }) {
  return <section className={`dynamic-card${className ? ` ${className}` : ""}`}><header><h2>{title}</h2>{asOf && <span className="section-asof">{asOf}</span>}</header>{children}</section>;
}

const ALLOCATION_BACKGROUNDS = ["#174f32", "#397357", "#89a797", "#c8cec5", "#68776b"] as const;

function AllocationBand({ targets, compact = false }: { targets: PortfolioTarget[]; compact?: boolean }) {
  if (!targets.length) return <div className="empty-state">No allocation</div>;
  return <div className={`allocation-band${compact ? " compact" : ""}`} aria-label={targetText(targets)}>
    {targets.map((target, index) => {
      const backgroundColor = ALLOCATION_BACKGROUNDS[index % ALLOCATION_BACKGROUNDS.length];
      return <div
        className="allocation-segment"
        key={`${target.symbol}-${target.role}`}
        style={{ backgroundColor, color: contrastingTextColor(backgroundColor), flexBasis: `${target.weight * 100}%`, flexGrow: target.weight }}
        title={`${target.symbol} ${pct(target.weight, 1)}`}
      >
        <strong>{target.symbol}</strong><span>{pct(target.weight, 1)}</span>
      </div>;
    })}
  </div>;
}

function EquityChart({ curve }: { curve: EquityPoint[] }) {
  const chart = useMemo(() => curve.filter((point) => point.equity > 0).map((point) => ({ date: point.date, equity: point.equity })), [curve]);
  const domain = useMemo<[number, number]>(() => {
    if (!chart.length) return [0.98, 1.02];
    const values = chart.map((point) => point.equity);
    return [Math.min(...values) / 1.02, Math.max(...values) * 1.02];
  }, [chart]);
  if (!chart.length) return <p className="page-note">No OOS equity data yet.</p>;
  return <div className="stage21-equity-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}>
    <CartesianGrid stroke="#dce1da" vertical={false} />
    <XAxis dataKey="date" minTickGap={40} tickFormatter={dateLabel} />
    <YAxis scale="log" domain={domain} allowDataOverflow tickFormatter={equityTick} />
    <Tooltip labelFormatter={(value) => typeof value === "string" ? dateLabel(value) : value} formatter={(value) => [equityTick(Number(value)), "Equity"]} />
    <Area type="monotone" dataKey="equity" stroke="#246b38" fill="#246b38" fillOpacity={0.12} isAnimationActive={false} />
  </AreaChart></ResponsiveContainer></div>;
}

export function MomentumApp({ initialDashboard }: { initialDashboard: DashboardPayload }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [data, setData] = useState(initialDashboard);
  const [refreshing, setRefreshing] = useState(false);

  const loadLatest = useCallback(async () => {
    setRefreshing(true);
    try {
      const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
      const response = await fetch(`${base}/data/dashboard.json?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Dashboard refresh failed: ${response.status}`);
      const body = await response.json() as { dashboard?: DashboardPayload };
      if (body.dashboard?.portfolioConfig?.strategyId && body.dashboard?.portfolioState?.strategyId) setData(body.dashboard);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => void loadLatest(), 60 * 1000);
    return () => window.clearInterval(id);
  }, [loadLatest]);

  return <div className="app-shell dynamic-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><TrendUpIcon weight="bold" /></div><div><strong>Momentum</strong><span>Stage21 Console</span></div></div>
      <nav>{tabs.map(([key, label, Icon]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}><Icon size={18} /><span>{label}</span></button>)}</nav>
      <div className="sidebar-foot"><span>Production</span><strong>{data.portfolioConfig.strategyId}</strong></div>
    </aside>
    <main>
      <div className="topbar">
        <div><span>Point-in-Time / next-open</span><strong>{tabs.find(([key]) => key === tab)?.[1]}</strong></div>
        <button className="refresh-button" onClick={() => void loadLatest()} disabled={refreshing}><ArrowsClockwiseIcon className={refreshing ? "spin" : ""} size={20} />Refresh</button>
      </div>
      <div className="dynamic-content">
        {data.warning && <div className="data-warning">{data.warning}</div>}
        {tab === "overview" && <Overview data={data} />}
        {tab === "universe" && <UniverseRanking data={data} />}
        {tab === "portfolio" && <Portfolio data={data} />}
        {tab === "oos" && <Oos data={data} />}
        {tab === "backtest" && <Backtest data={data} />}
        {tab === "schedule" && <Schedule data={data} />}
      </div>
    </main>
  </div>;
}

const price = (value: number | null | undefined) => value == null ? "—" : value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const asOfLabel = (value: string) => {
  if (!value) return "as-of —";
  return `as-of ${value.includes("T") ? updatedAt(value) : usCloseJst(value)}`;
};

function Portfolio({ data }: { data: DashboardPayload }) {
  const positions = [...data.portfolioState.holdings, ...data.portfolioState.targets
    .filter((target) => target.symbol !== "CASH" && !data.portfolioState.holdings.some((holding) => holding.symbol === target.symbol))
    .map((target) => ({ symbol: target.symbol, entryPrice: null, currentPrice: null, targetWeight: target.weight, role: target.role }))]
    .map((holding) => {
      const latest = data.latestPrices?.[holding.symbol];
      const currentPrice = latest?.price ?? holding.currentPrice;
      return { ...holding, currentPrice, pnl: holding.entryPrice == null || currentPrice == null ? null : currentPrice / holding.entryPrice - 1, priceAsOf: latest?.asOf ?? data.portfolioState.asOf };
    });
  const latestAsOf = positions.map((position) => position.priceAsOf).filter(Boolean).sort().at(-1) ?? data.portfolioState.asOf;

  return <div className="dynamic-stack"><Section title="Current Positions" asOf={asOfLabel(latestAsOf)}>
    <div className="table-scroll portfolio-table">
      {positions.length ? <table className="dynamic-table positions-table"><thead><tr><th>Ticker</th><th>Entry Price</th><th>Current Price</th><th>P/L</th></tr></thead>
        <tbody>{positions.map((position) => <tr key={position.symbol}>
          <td className="ticker-data" data-label="Ticker"><strong>{position.symbol}</strong></td>
          <td data-label="Entry Price">{price(position.entryPrice)}</td>
          <td data-label="Current Price">{price(position.currentPrice)}</td>
          <td data-label="P/L"><strong className={position.pnl != null && position.pnl < 0 ? "tone-bad" : "tone-good"}>{pct(position.pnl, 2)}</strong></td>
        </tr>)}</tbody></table> : <div className="empty-state">No open positions</div>}
    </div>
  </Section></div>;
}

function Overview({ data }: { data: DashboardPayload }) {
  const [detail, setDetail] = useState<DetailKey | null>(null);
  const [latestCompletedSession, setLatestCompletedSession] = useState<string | null>(null);
  const portfolio = data.portfolioState;
  const gate = evaluateOosActionGate(data.oos);
  const action = portfolio.nextAction;
  const actionLabel = action.type === "REBALANCE_NEXT_OPEN" ? "REBALANCE" : action.type === "HOLD" ? "HOLD" : "REVIEW";
  const execution = action.executionDate ? usOpenJst(action.executionDate) : "NO ORDER";
  const executionState = action.executionDate ? "NEXT OPEN" : "NO ORDER";
  const nportDeadline = data.nportOperations?.nextImportDeadlineAt ? updatedAt(data.nportOperations.nextImportDeadlineAt) : "NOT SET";
  const nonLatestClose = latestCompletedSession != null && (!portfolio.asOf || portfolio.asOf < latestCompletedSession);

  useEffect(() => {
    const update = () => setLatestCompletedSession(latestCompletedUsTradingSession());
    update();
    const id = window.setInterval(update, 60 * 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!detail) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setDetail(null); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [detail]);

  const title = detail === "regime" ? "Regime" : detail === "action" ? "Action" : detail === "execution" ? "Execution" : detail === "nport" ? "N-PORT Deadline" : detail === "target" ? "Target" : detail === "cftc" ? "CFTC" : detail === "m3" ? "M3 Deep" : detail === "fixed60" ? "Inner Fixed60" : "OOS Gate";

  return <div className="dynamic-stack">
    <Section title="Next Action">
      <div className="next-action next-action-stage21">
        <div className="next-action-primary">
          <button type="button" className="next-action-cell" onClick={() => setDetail("regime")}><span>Regime</span><strong>{portfolio.regime}</strong></button>
          <button type="button" className="next-action-cell" onClick={() => setDetail("action")}><span>Action</span><div className="action-value-line"><strong>{actionLabel}</strong>{nonLatestClose && <span className="close-basis-warning" title={`Decision uses ${portfolio.asOf || "no"} daily close; latest completed session is ${latestCompletedSession}.`}>STALE</span>}</div></button>
          <button type="button" className="next-action-cell execution-cell" onClick={() => setDetail("execution")}><span>Execution (JST)</span><strong>{execution}</strong></button>
        </div>
        <div className="next-action-secondary">
          <button type="button" className="next-action-cell nport-deadline-cell" onClick={() => setDetail("nport")}><span>N-PORT Deadline (JST)</span><strong>{nportDeadline}</strong></button>
          <button type="button" className="next-action-cell target-cell" onClick={() => setDetail("target")}><span>Target</span><AllocationBand targets={action.targets} compact /></button>
        </div>
      </div>
    </Section>

    <div className="dynamic-metric-grid four overview-status-grid">
      <StatusMetric label="CFTC" value={portfolio.cftc.yellow ? "YELLOW" : "CLEAR"} onClick={() => setDetail("cftc")} />
      <StatusMetric label="M3 Deep" value={portfolio.m3.deep ? "ON" : "OFF"} onClick={() => setDetail("m3")} />
      <StatusMetric label="Inner Fixed60" value={portfolio.fixed60.riskState} onClick={() => setDetail("fixed60")} />
      <StatusMetric label="OOS Gate" value={gate.level} onClick={() => setDetail("oos")} />
    </div>

    <div className="dynamic-metric-grid four overview-input-grid">
      <Metric label="CFTC Used (PIT)" value={dateLabel(portfolio.cftc.reportDate)} nowrap />
      <Metric label="CFTC Net" value={portfolio.cftc.net == null ? "—" : Math.round(portfolio.cftc.net).toLocaleString()} />
      <Metric label="Prior 4W" value={portfolio.cftc.priorNet == null ? "—" : Math.round(portfolio.cftc.priorNet).toLocaleString()} />
      <Metric label="M3 Gap" value={pct(portfolio.m3.gap)} />
    </div>

    {detail && <div className="modal-backdrop" onMouseDown={() => setDetail(null)}>
      <div className="action-modal action-detail-modal" role="dialog" aria-modal="true" aria-labelledby="action-detail-title" onMouseDown={(event) => event.stopPropagation()}>
        <header><div><span>DETAIL</span><h2 id="action-detail-title">{title}</h2></div><button type="button" aria-label="Close" onClick={() => setDetail(null)}><XIcon size={20} /></button></header>
        <div className="action-detail-body">
          {detail === "regime" && <DefinitionList current={portfolio.regime} items={[
            { name: "NORMAL", meaning: "Base allocation: Fixed60 85%, GLDM 15%, Cash 0%." },
            { name: "YELLOW", meaning: "CFTC caution allocation: Fixed60 55.5%, GLDM 22.5%, Cash 22%." },
            { name: "DEEP", meaning: "M3 defensive allocation: Fixed60 25.5%, GLDM 30%, Cash 44.5%." },
          ]} />}
          {detail === "action" && <DefinitionList current={actionLabel} items={[
            { name: "HOLD", meaning: "Target is unchanged. No rebalance order is created." },
            { name: "REBALANCE", meaning: "Target changed. Rebalance is scheduled for the next US market open." },
          ]} />}
          {detail === "execution" && <DefinitionList current={executionState} items={[
            { name: "NO ORDER", meaning: "No execution is currently scheduled." },
            { name: "NEXT OPEN", meaning: "Execute the displayed target at the next US market open after close confirmation." },
          ]} />}
          {detail === "nport" && <DefinitionList current={nportDeadline} items={[
            { name: nportDeadline, meaning: "Complete the next quarterly N-PORT import before this cutoff." },
            { name: "FALLBACK", meaning: "If the deadline is missed or import validation fails, the prior valid Universe remains active." },
          ]} />}
          {detail === "target" && <><AllocationBand targets={action.targets} /><p>100% total / no leverage</p></>}
          {detail === "cftc" && <DefinitionList current={portfolio.cftc.yellow ? "YELLOW" : "CLEAR"} items={[
            { name: "CLEAR", meaning: "The latest PIT-eligible Asset Manager net position is not below the report from four releases earlier." },
            { name: "YELLOW", meaning: "The latest PIT-eligible net position is below the report from four releases earlier." },
          ]} />}
          {detail === "m3" && <DefinitionList current={portfolio.m3.deep ? "ON" : "OFF"} items={[
            { name: "OFF", meaning: "The defensive M3 condition is inactive." },
            { name: "ON", meaning: "Core 20-session return is negative and trails QQQ by at least 10 percentage points. Exit requires five confirmations above the -3 point recovery gap." },
          ]} />}
          {detail === "fixed60" && <DefinitionList current={portfolio.fixed60.riskState} items={[
            { name: "INVESTED", meaning: "The inner momentum portfolio is invested." },
            { name: "LOCKED_MARKET", meaning: "The QQQ monthly gate is Risk Off. Portfolio remains locked in Cash." },
            { name: "LOCKED_STOP", meaning: "An individual stop triggered a full-portfolio exit and recovery lock." },
            { name: "LOCKED_CIRCUIT", meaning: "The portfolio circuit breaker triggered a full exit and recovery lock." },
            { name: "WAITING_RECOVERY", meaning: "Recovery conditions have not completed ten consecutive closes." },
            { name: "READY_NEXT_OPEN", meaning: "Recovery is confirmed. Entry is scheduled for the next US market open." },
            { name: "CASH", meaning: "No inner momentum positions are currently held." },
          ]} />}
          {detail === "oos" && <DefinitionList current={gate.level} items={[
            { name: "GREEN", meaning: "No preregistered OOS gate is breached. Continue the frozen rules." },
            { name: "AMBER", meaning: "OOS drawdown reached the 17% review boundary. Review without changing or automatically stopping the strategy." },
            { name: "RED", meaning: "A kill or long-horizon hurdle is breached. Block new entries and move to Cash at the next US market open." },
          ]} />}
        </div>
      </div>
    </div>}
  </div>;
}

function SortHeader({ label, sortKey, activeKey, direction, onSort }: { label: string; sortKey: CombinedSortKey; activeKey: CombinedSortKey; direction: SortDirection; onSort: (key: CombinedSortKey) => void }) {
  const active = activeKey === sortKey;
  const Icon = !active ? CaretUpDownIcon : direction === "asc" ? CaretUpIcon : CaretDownIcon;
  return <th aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}><button type="button" className={active ? "sort-button active" : "sort-button"} onClick={() => onSort(sortKey)}>{label}<Icon size={12} weight="bold" /></button></th>;
}

function UniverseRanking({ data }: { data: DashboardPayload }) {
  const [sortKey, setSortKey] = useState<CombinedSortKey>("universeRank");
  const [direction, setDirection] = useState<SortDirection>("asc");

  const rows = useMemo<CombinedRow[]>(() => {
    const candidates = new Map((data.currentSignal?.candidates ?? []).map((candidate) => [candidate.symbol, candidate]));
    return (data.currentUniverse?.symbols ?? []).map((member) => {
      const candidate = candidates.get(member.symbol) ?? null;
      return { ...member, candidate, momentumRank: candidate?.rank ?? null, status: candidate ? (candidate.eligible ? "ELIGIBLE" : candidate.exclusionReason ?? "EXCLUDED") : "NOT RANKED" };
    });
  }, [data.currentSignal?.candidates, data.currentUniverse?.symbols]);

  const sortedRows = useMemo(() => {
    const valueFor = (row: CombinedRow): string | number | null => {
      if (sortKey === "momentumRank") return row.momentumRank;
      if (sortKey === "threeMonth") return row.candidate?.threeMonth ?? null;
      if (sortKey === "sixMonth") return row.candidate?.sixMonth ?? null;
      if (sortKey === "score") return row.candidate?.score ?? null;
      if (sortKey === "status") return row.status;
      return row[sortKey];
    };
    return [...rows].sort((left, right) => {
      const a = valueFor(left), b = valueFor(right);
      if (a == null && b == null) return left.symbol.localeCompare(right.symbol);
      if (a == null) return 1;
      if (b == null) return -1;
      const result = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "en", { numeric: true });
      return direction === "asc" ? result : -result;
    });
  }, [direction, rows, sortKey]);

  const changeSort = (key: CombinedSortKey) => {
    if (key === sortKey) setDirection((current) => current === "asc" ? "desc" : "asc");
    else { setSortKey(key); setDirection("asc"); }
  };

  return <Section title="Universe"><div className="table-scroll"><table className="dynamic-table combined-ranking-table">
    <thead><tr>
      <SortHeader label="Universe" sortKey="universeRank" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="Ticker" sortKey="symbol" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="ETF Count" sortKey="etfCount" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="Universe Score" sortKey="universeScore" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="Momentum" sortKey="momentumRank" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="3M" sortKey="threeMonth" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="6M" sortKey="sixMonth" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="Score" sortKey="score" activeKey={sortKey} direction={direction} onSort={changeSort} />
      <SortHeader label="Status" sortKey="status" activeKey={sortKey} direction={direction} onSort={changeSort} />
    </tr></thead>
    <tbody>{sortedRows.map((row) => <tr key={row.symbol}>
      <td>{row.universeRank}</td><td><strong>{row.symbol}</strong></td><td>{row.etfCount}</td><td>{row.universeScore.toFixed(2)}</td><td>{row.momentumRank ?? "—"}</td><td>{pct(row.candidate?.threeMonth)}</td><td>{pct(row.candidate?.sixMonth)}</td><td>{row.candidate?.score == null ? "—" : row.candidate.score.toFixed(3)}</td><td>{row.status}</td>
    </tr>)}</tbody>
  </table></div></Section>;
}

function Oos({ data }: { data: DashboardPayload }) {
  const gate = evaluateOosActionGate(data.oos);
  return <div className="dynamic-stack"><Section title="Forward OOS" className="metric-section"><div className="dynamic-metric-grid five">
    <Metric label="Start" value={dateLabel(data.oos.startedAt)} nowrap />
    <Metric label="As of" value={dateLabel(data.oos.asOf)} nowrap />
    <Metric label="CAGR" value={pct(data.oos.stats.cagr)} />
    <Metric label="MaxDD" value={pct(data.oos.stats.maxDrawdown)} />
    <Metric label="Gate" value={gate.level} />
  </div></Section><Section title="OOS Equity · Log Scale"><EquityChart curve={data.oos.equityCurve} /></Section><p className="page-note">Validated OOS data · dashboard refreshes automatically every minute · updated {data.generatedAt ? updatedAt(data.generatedAt) : "—"}</p></div>;
}

function Backtest({ data }: { data: DashboardPayload }) {
  const reference = data.portfolioConfig.researchReference;
  return <div className="dynamic-stack">
    <div className="dynamic-metric-grid five">
      <Metric label="Historical CAGR" value={pct(data.backtest.stats.cagr)} /><Metric label="Historical MaxDD" value={pct(data.backtest.stats.maxDrawdown)} /><Metric label="Planning Proxy" value={pct(reference.planningCagrProxy)} /><Metric label="Rolling36 Median" value={pct(reference.rolling36MedianCagr)} /><Metric label="Rolling36 Worst" value={pct(reference.rolling36WorstCagr)} />
    </div>
    <Section title="Stage21 Equity · Log Scale"><EquityChart curve={data.backtest.equityCurve} /></Section>
    <p className="page-note">Planning proxy is not a forward forecast.</p>
  </div>;
}

function Schedule({ data }: { data: DashboardPayload }) {
  return <div className="dynamic-stack"><Section title="Configuration"><div className="simple-table">
    <div><strong>Production ID</strong><span>{data.portfolioConfig.strategyId}</span></div><div><strong>OOS Start</strong><span>{dateLabel(data.portfolioConfig.oosStartDate)}</span></div><div><strong>Execution</strong><span>Close confirmation → next US open</span></div><div><strong>Cost</strong><span>{pct(data.portfolioConfig.execution.transactionCost, 2)} / side</span></div><div><strong>N-PORT Deadline</strong><span>{data.nportOperations?.nextImportDeadlineAt ? updatedAt(data.nportOperations.nextImportDeadlineAt) : "—"}</span></div>
  </div></Section></div>;
}
