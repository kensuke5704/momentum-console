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
import { evaluateOosActionGate } from "@/lib/oos-action-gate";
import type { PortfolioTarget } from "@/lib/portfolio-types";
import type { DashboardPayload, EquityPoint, MomentumCandidate, UniverseMember } from "@/lib/types";

type Tab = "overview" | "universe" | "portfolio" | "oos" | "backtest" | "schedule";
type DetailKey = "regime" | "action" | "execution" | "target" | "cftc" | "m3" | "fixed60" | "oos";
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
  ["universe", "Universe / Ranking", DatabaseIcon],
  ["portfolio", "Portfolio", WalletIcon],
  ["oos", "OOS", ChartLineUpIcon],
  ["backtest", "Backtest", ClockCounterClockwiseIcon],
  ["schedule", "Settings", GearIcon],
] as const;

const pct = (value: number | null | undefined, digits = 1) =>
  value == null ? "—" : `${(value * 100).toFixed(digits)}%`;

const updatedAt = (value: string) =>
  new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));

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

const targetText = (targets: PortfolioTarget[]) =>
  targets.map((target) => `${target.symbol} ${pct(target.weight, 1)}`).join(" / ") || "—";

function Metric({ label, value, nowrap = false }: { label: string; value: string; nowrap?: boolean }) {
  return <div className={`dynamic-metric${nowrap ? " metric-nowrap" : ""}`}><span>{label}</span><strong>{value}</strong></div>;
}

function StatusMetric({ label, value, onClick }: { label: string; value: string; onClick: () => void }) {
  return <button type="button" className="dynamic-metric interactive-metric" onClick={onClick} aria-label={`${label} details`}>
    <span>{label}</span><strong>{value}</strong>
  </button>;
}

function Section({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return <section className={`dynamic-card${className ? ` ${className}` : ""}`}><header><h2>{title}</h2></header>{children}</section>;
}

function AllocationBand({ targets, compact = false }: { targets: PortfolioTarget[]; compact?: boolean }) {
  if (!targets.length) return <div className="empty-state">No allocation</div>;
  return <div className={`allocation-band${compact ? " compact" : ""}`} aria-label={targetText(targets)}>
    {targets.map((target, index) => <div
      className={`allocation-segment allocation-segment-${index % 5}`}
      key={`${target.symbol}-${target.role}`}
      style={{ flexBasis: `${target.weight * 100}%`, flexGrow: target.weight }}
      title={`${target.symbol} ${pct(target.weight, 1)}`}
    >
      <strong>{target.symbol}</strong><span>{pct(target.weight, 1)}</span>
    </div>)}
  </div>;
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
      const body = await response.json() as { dashboard: DashboardPayload };
      setData(body.dashboard);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => void loadLatest(), 5 * 60 * 1000);
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

function Overview({ data }: { data: DashboardPayload }) {
  const [detail, setDetail] = useState<DetailKey | null>(null);
  const portfolio = data.portfolioState;
  const gate = evaluateOosActionGate(data.oos);
  const action = portfolio.nextAction;
  const actionLabel = action.type === "REBALANCE_NEXT_OPEN" ? "REBALANCE" : action.type === "HOLD" ? "HOLD" : "REVIEW";
  const execution = action.executionDate ? usOpenJst(action.executionDate) : "NO ORDER";

  useEffect(() => {
    if (!detail) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setDetail(null); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [detail]);

  const title = detail === "regime" ? "Regime" : detail === "action" ? "Action" : detail === "execution" ? "Execution" : detail === "target" ? "Target" : detail === "cftc" ? "CFTC" : detail === "m3" ? "M3 Deep" : detail === "fixed60" ? "Inner Fixed60" : "OOS Gate";

  return <div className="dynamic-stack">
    <Section title="Next Action">
      <div className="next-action next-action-stage21">
        <button type="button" className="next-action-cell" onClick={() => setDetail("regime")}><span>Regime</span><strong>{portfolio.regime}</strong></button>
        <button type="button" className="next-action-cell" onClick={() => setDetail("action")}><span>Action</span><strong>{actionLabel}</strong></button>
        <button type="button" className="next-action-cell execution-cell" onClick={() => setDetail("execution")}><span>Execution (JST)</span><strong>{execution}</strong></button>
        <button type="button" className="next-action-cell target-cell" onClick={() => setDetail("target")}><span>Target</span><AllocationBand targets={action.targets} compact /></button>
      </div>
    </Section>

    <div className="dynamic-metric-grid four overview-status-grid">
      <StatusMetric label="CFTC" value={portfolio.cftc.yellow ? "YELLOW" : "CLEAR"} onClick={() => setDetail("cftc")} />
      <StatusMetric label="M3 Deep" value={portfolio.m3.deep ? "ON" : "OFF"} onClick={() => setDetail("m3")} />
      <StatusMetric label="Inner Fixed60" value={portfolio.fixed60.riskState} onClick={() => setDetail("fixed60")} />
      <StatusMetric label="OOS Gate" value={gate.level} onClick={() => setDetail("oos")} />
    </div>

    <Section title="Current Allocation"><AllocationBand targets={portfolio.targets} /></Section>

    {detail && <div className="modal-backdrop" onMouseDown={() => setDetail(null)}>
      <div className="action-modal action-detail-modal" role="dialog" aria-modal="true" aria-labelledby="action-detail-title" onMouseDown={(event) => event.stopPropagation()}>
        <header><div><span>DETAIL</span><h2 id="action-detail-title">{title}</h2></div><button type="button" aria-label="Close" onClick={() => setDetail(null)}><XIcon size={20} /></button></header>
        <div className="action-detail-body">
          {detail === "regime" && <><strong className="action-detail-value">{portfolio.regime}</strong><dl className="action-detail-grid">
            <div><dt>CFTC</dt><dd>{portfolio.cftc.yellow ? "YELLOW" : "CLEAR"}</dd></div>
            <div><dt>M3 Deep</dt><dd>{portfolio.m3.deep ? "ON" : "OFF"}</dd></div>
            <div><dt>Inner Fixed60</dt><dd>{portfolio.fixed60.riskState}</dd></div>
            <div><dt>OOS Gate</dt><dd>{gate.level}</dd></div>
          </dl></>}
          {detail === "action" && <><strong className="action-detail-value">{actionLabel}</strong><p>{action.reason}</p></>}
          {detail === "execution" && <><strong className="action-detail-value nowrap">{execution}</strong><p>{action.executionDate ? `${action.executionDate} US market open` : "No order scheduled."}</p></>}
          {detail === "target" && <><AllocationBand targets={action.targets} /><p>100% total / no leverage</p></>}
          {detail === "cftc" && <><strong className="action-detail-value">{portfolio.cftc.yellow ? "YELLOW" : "CLEAR"}</strong><dl className="action-detail-grid three">
            <div><dt>CFTC Used (PIT)</dt><dd className="nowrap">{portfolio.cftc.reportDate ?? "—"}</dd></div>
            <div><dt>Net</dt><dd>{portfolio.cftc.net == null ? "—" : Math.round(portfolio.cftc.net).toLocaleString()}</dd></div>
            <div><dt>Prior 4W</dt><dd>{portfolio.cftc.priorNet == null ? "—" : Math.round(portfolio.cftc.priorNet).toLocaleString()}</dd></div>
          </dl></>}
          {detail === "m3" && <><strong className="action-detail-value">{portfolio.m3.deep ? "ON" : "OFF"}</strong><dl className="action-detail-grid">
            <div><dt>Core 20D</dt><dd>{pct(portfolio.m3.coreReturn20)}</dd></div>
            <div><dt>QQQ 20D</dt><dd>{pct(portfolio.m3.qqqReturn20)}</dd></div>
            <div><dt>Gap</dt><dd>{pct(portfolio.m3.gap)}</dd></div>
            <div><dt>Recovery</dt><dd>{portfolio.m3.recoveryConfirm}</dd></div>
          </dl></>}
          {detail === "fixed60" && <><strong className="action-detail-value">{portfolio.fixed60.riskState}</strong><dl className="action-detail-grid two">
            <div><dt>Strategy</dt><dd>{portfolio.fixed60.strategyId}</dd></div>
            <div><dt>Positions</dt><dd>{portfolio.fixed60.symbols.length ? portfolio.fixed60.symbols.map((symbol, index) => `${symbol} ${pct(portfolio.fixed60.innerWeights[index], 0)}`).join(" / ") : "CASH"}</dd></div>
          </dl></>}
          {detail === "oos" && <><strong className="action-detail-value">{gate.level}</strong><p>{gate.instruction}</p><p className="detail-secondary">{gate.reason}</p></>}
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

  return <Section title="Universe / Momentum Ranking"><div className="table-scroll"><table className="dynamic-table combined-ranking-table">
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

function Portfolio({ data }: { data: DashboardPayload }) {
  const portfolio = data.portfolioState;
  return <div className="dynamic-stack">
    <Section title="Production Target"><AllocationBand targets={portfolio.targets} /></Section>
    <Section title="Regime Inputs" className="metric-section"><div className="dynamic-metric-grid five">
      <Metric label="Regime" value={portfolio.regime} />
      <Metric label="CFTC Used (PIT)" value={portfolio.cftc.reportDate ?? "—"} nowrap />
      <Metric label="CFTC Net" value={portfolio.cftc.net == null ? "—" : Math.round(portfolio.cftc.net).toLocaleString()} />
      <Metric label="Prior 4W" value={portfolio.cftc.priorNet == null ? "—" : Math.round(portfolio.cftc.priorNet).toLocaleString()} />
      <Metric label="M3 Gap" value={pct(portfolio.m3.gap)} />
    </div></Section>
  </div>;
}

function Oos({ data }: { data: DashboardPayload }) {
  const gate = evaluateOosActionGate(data.oos);
  return <div className="dynamic-stack"><Section title="Forward OOS" className="metric-section"><div className="dynamic-metric-grid five">
    <Metric label="Start" value={data.oos.startedAt} nowrap />
    <Metric label="As of" value={data.oos.asOf ?? "—"} nowrap />
    <Metric label="CAGR" value={pct(data.oos.stats.cagr)} />
    <Metric label="MaxDD" value={pct(data.oos.stats.maxDrawdown)} />
    <Metric label="Gate" value={gate.level} />
  </div></Section></div>;
}

function Backtest({ data }: { data: DashboardPayload }) {
  const reference = data.portfolioConfig.researchReference;
  const chart = useMemo(() => data.backtest.equityCurve.map((point: EquityPoint) => ({ date: point.date, equity: point.equity })), [data.backtest.equityCurve]);
  return <div className="dynamic-stack">
    <div className="dynamic-metric-grid five">
      <Metric label="Historical CAGR" value={pct(data.backtest.stats.cagr)} /><Metric label="Historical MaxDD" value={pct(data.backtest.stats.maxDrawdown)} /><Metric label="Planning Proxy" value={pct(reference.planningCagrProxy)} /><Metric label="Rolling36 Median" value={pct(reference.rolling36MedianCagr)} /><Metric label="Rolling36 Worst" value={pct(reference.rolling36WorstCagr)} />
    </div>
    <Section title="Stage21 Equity"><div className="stage21-equity-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><CartesianGrid stroke="#dce1da" vertical={false} /><XAxis dataKey="date" minTickGap={40} /><YAxis /><Tooltip /><Area type="monotone" dataKey="equity" stroke="#246b38" fill="#246b38" fillOpacity={0.12} isAnimationActive={false} /></AreaChart></ResponsiveContainer></div></Section>
    <p className="page-note">Planning proxy is not a forward forecast.</p>
  </div>;
}

function Schedule({ data }: { data: DashboardPayload }) {
  return <div className="dynamic-stack"><Section title="Configuration"><div className="simple-table">
    <div><strong>Production ID</strong><span>{data.portfolioConfig.strategyId}</span></div><div><strong>OOS Start</strong><span>{data.portfolioConfig.oosStartDate}</span></div><div><strong>Execution</strong><span>Close confirmation → next US open</span></div><div><strong>Cost</strong><span>{pct(data.portfolioConfig.execution.transactionCost, 2)} / side</span></div><div><strong>N-PORT Deadline</strong><span>{data.nportOperations?.nextImportDeadlineAt ? updatedAt(data.nportOperations.nextImportDeadlineAt) : "—"}</span></div>
  </div></Section></div>;
}
