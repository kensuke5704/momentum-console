"use client";

import {
  ArrowClockwiseIcon,
  ArrowDownIcon,
  ArrowUpIcon,
  ChartLineUpIcon,
  CheckCircleIcon,
  GearSixIcon,
  ListChecksIcon,
  MagnifyingGlassIcon,
  ScalesIcon,
  SlidersHorizontalIcon,
  TargetIcon,
  WarningCircleIcon,
  WalletIcon,
  XIcon,
} from "@phosphor-icons/react";
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  DEFAULT_STRATEGY,
  getTargetAmountUsd,
  normalizeStrategyConfig,
  TICKERS,
} from "@/lib/config";
import { buildDashboard } from "@/lib/momentum";
import { CandidateManagerView } from "@/components/candidate-manager-view";
import { OperationScheduleSection } from "@/components/operation-schedule-section";
import {
  fetchYahooHistoriesInBrowser,
  fetchYahooHistoryInBrowser,
} from "@/lib/yahoo-client";
import type {
  BacktestRow,
  DashboardPayload,
  PricePoint,
  StrategyConfig,
} from "@/lib/types";

type View =
  | "overview"
  | "screener"
  | "portfolio"
  | "backtest"
  | "comparison"
  | "settings";
type HoldingMap = Record<string, number>;
type MarketDataFile = {
  generatedAt: string;
  histories: Record<string, PricePoint[]>;
  dashboard: DashboardPayload;
};

const USD_JPY_SYMBOL = "JPY=X";
const USD_JPY_REFRESH_INTERVAL_MS = 15 * 60 * 1000;
const STRATEGY_STORAGE_KEY = "momentum-strategy";
const STRATEGY_STORAGE_VERSION_KEY = "momentum-strategy-version";
const STRATEGY_STORAGE_VERSION = "2026-08-topn-weights-v4";

function withLatestUsdJpy(
  strategy: StrategyConfig,
  priceHistories: Record<string, PricePoint[]>,
) {
  const latest = priceHistories[USD_JPY_SYMBOL]?.at(-1)?.close;
  if (typeof latest !== "number" || !Number.isFinite(latest) || latest <= 0) {
    return normalizeStrategyConfig(strategy);
  }
  return normalizeStrategyConfig({ ...strategy, usdJpy: latest });
}

function mergeHistories(
  base: Record<string, PricePoint[]>,
  updates: Record<string, PricePoint[]>,
) {
  const merged = { ...base };
  for (const [symbol, points] of Object.entries(updates)) {
    const byDate = new Map(
      (base[symbol] ?? []).map((point) => [point.date, point]),
    );
    for (const point of points) byDate.set(point.date, point);
    merged[symbol] = [...byDate.values()].sort((a, b) =>
      a.date.localeCompare(b.date)
    );
  }
  return merged;
}

const views: Array<{
  id: View;
  label: string;
  icon: typeof ChartLineUpIcon;
}> = [
  { id: "overview", label: "概要", icon: ChartLineUpIcon },
  { id: "screener", label: "銘柄分析", icon: ListChecksIcon },
  { id: "portfolio", label: "ポートフォリオ", icon: WalletIcon },
  { id: "backtest", label: "バックテスト", icon: TargetIcon },
  { id: "comparison", label: "候補組み替え", icon: ScalesIcon },
  { id: "settings", label: "戦略設定", icon: GearSixIcon },
];

const money = new Intl.NumberFormat("ja-JP", {
  maximumFractionDigits: 0,
});
const decimal = new Intl.NumberFormat("ja-JP", {
  maximumFractionDigits: 2,
});

function percent(value: number | null, digits = 1) {
  if (value === null || !Number.isFinite(value)) return "N/A";
  return new Intl.NumberFormat("ja-JP", {
    style: "percent",
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function compactDate(value: string) {
  return value ? value.replaceAll("-", ".") : "未取得";
}

function allocationMonth(value: string) {
  const [yearText, monthText] = value.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  if (!Number.isInteger(year) || !Number.isInteger(month)) return "";
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  return `${nextYear}.${String(nextMonth).padStart(2, "0")}`;
}

function Metric({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "positive" | "negative" | "neutral";
}) {
  return (
    <div className="metric">
      <p>{label}</p>
      <strong className={`metric-value ${tone}`}>{value}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

function SourceBadge({ payload }: { payload: DashboardPayload }) {
  return (
    <div className={`source-badge ${payload.source}`}>
      {payload.source === "live" ? (
        <CheckCircleIcon weight="fill" />
      ) : (
        <WarningCircleIcon weight="fill" />
      )}
      <span>{payload.source === "live" ? "ライブ価格" : "シート値"}</span>
    </div>
  );
}

function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="empty-state">
      <MagnifyingGlassIcon size={26} />
      <strong>{title}</strong>
      <p>{body}</p>
    </div>
  );
}

function LoadingLine() {
  return <span className="loading-line" aria-label="更新中" />;
}

function ScoreChange({ value }: { value: number | null }) {
  const positive = (value ?? 0) >= 0;
  return (
    <span className={`change ${positive ? "up" : "down"}`}>
      {positive ? <ArrowUpIcon /> : <ArrowDownIcon />}
      {percent(value)}
    </span>
  );
}

function Overview({
  data,
  loading,
  onNavigate,
}: {
  data: DashboardPayload;
  loading: boolean;
  onNavigate: (view: View) => void;
}) {
  const allocationIsCash = data.market.allocationStatus !== "Invest";
  const insufficient =
    data.market.allocationStatus === "CashInsufficient";
  const allocationLabel = allocationIsCash ? "Cash" : "RiskOn";
  const chartData = data.backtest.rows
    .filter((row) => typeof row.equity === "number")
    .map((row) => ({
      date: row.signalMonth.slice(0, 7),
      equity: (row.equity ?? 1) * 100,
    }));
  const latestReturns = data.backtest.rows
    .filter(
      (row) =>
        typeof row.monthlyReturn === "number" &&
        !row.provisional,
    )
    .slice(-8)
    .map((row) => ({
      date: row.signalMonth.slice(2, 7).replace("-", "/"),
      value: (row.monthlyReturn ?? 0) * 100,
    }));
  const monthToDateValues = data.portfolio
    .map((row) => row.monthToDate)
    .filter((value): value is number => typeof value === "number");
  const averageMonthToDate =
    monthToDateValues.length === data.portfolio.length &&
    monthToDateValues.length > 0
      ? monthToDateValues.reduce((sum, value) => sum + value, 0) /
        monthToDateValues.length
      : null;

  return (
    <div className="view-stack">
      {data.warning ? (
        <div className="warning-banner" role="status">
          <WarningCircleIcon size={20} weight="fill" />
          <span>{data.warning}</span>
        </div>
      ) : null}

      <section className="market-panel">
        <div className="decision-strip">
          <span>現在の配分判定</span>
          <strong>{allocationLabel}</strong>
          <p>
            {insufficient
              ? `QQQはRiskOnですが、採用候補が${decimal.format(data.market.selectedCount)}/${decimal.format(data.config.topN)}銘柄のため、ルールにより全額現金です。`
              : data.market.state === "RiskOn"
                ? "QQQは10か月移動平均を上回っています。選定銘柄への配分シグナルです。"
                : "QQQは10か月移動平均以下です。新規配分を停止するシグナルです。"}
          </p>
          <span className="decision-date">
            判定基準日: {compactDate(data.market.decisionDate)}（確定月末）
          </span>
        </div>

        <div className="market-copy">
          <div className="section-label">EVIDENCE</div>
          <div className="market-values">
            <Metric
              label="QQQ"
              value={
                data.market.qqq === null
                  ? "N/A"
                  : `$${decimal.format(data.market.qqq)}`
              }
            />
            <Metric
              label="10M MA"
              value={
                data.market.ma10 === null
                  ? "N/A"
                  : `$${decimal.format(data.market.ma10)}`
              }
            />
            <Metric
              label="QQQ score"
              value={percent(data.market.qqqScore)}
              tone={(data.market.qqqScore ?? 0) >= 0 ? "positive" : "negative"}
            />
          </div>
        </div>

        <div className="return-visual">
          <div className="visual-head">
            <div>
              <span>直近8か月</span>
              <strong>単月リターン</strong>
            </div>
            {loading ? <LoadingLine /> : null}
          </div>
          <div className="mini-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={latestReturns}>
                <ReferenceLine y={0} stroke="var(--line-strong)" />
                <Bar
                  dataKey="value"
                  radius={[4, 4, 4, 4]}
                  isAnimationActive={false}
                >
                  {latestReturns.map((row) => (
                    <Cell
                      key={row.date}
                      fill={row.value < 0 ? "var(--danger)" : "var(--accent)"}
                    />
                  ))}
                </Bar>
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                />
                <Tooltip content={<ReturnTooltip />} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {!allocationIsCash ? (
        <section className="pick-section">
          <div className="section-heading">
            <div>
              <h2>
                今月の採用銘柄
                {allocationMonth(data.market.decisionDate)
                  ? `（${allocationMonth(data.market.decisionDate)}）`
                  : ""}
              </h2>
            </div>
            <button className="text-button" onClick={() => onNavigate("portfolio")}>
              配分を確認
              <ArrowUpIcon className="arrow-right" />
            </button>
          </div>
          <div className="pick-table-head" aria-hidden="true">
            <span>RANK</span>
            <span>TICKER / THEME</span>
            <span>現在値</span>
            <span>月初来</span>
            <span>1M</span>
            <span>3M</span>
            <span>6M</span>
            <span>SCORE</span>
          </div>
          <div className="pick-grid">
            {data.portfolio.map((row, index) => (
              <article className="pick-row" key={row.symbol}>
                <span className="pick-number">{String(index + 1).padStart(2, "0")}</span>
                <div className="ticker-block">
                  <strong>{row.symbol}</strong>
                  <span>{row.genre}</span>
                </div>
                <div className="pick-price">
                  <strong>
                    {row.current === null ? "N/A" : `$${decimal.format(row.current)}`}
                  </strong>
                </div>
                <span
                  className={`pick-month-to-date ${(row.monthToDate ?? 0) < 0 ? "negative" : ""}`}
                >
                  {percent(row.monthToDate)}
                </span>
                <span className={(row.oneMonth ?? 0) < 0 ? "negative" : ""}>
                  {percent(row.oneMonth)}
                </span>
                <span className={(row.threeMonth ?? 0) < 0 ? "negative" : ""}>
                  {percent(row.threeMonth)}
                </span>
                <span className={(row.sixMonth ?? 0) < 0 ? "negative" : ""}>
                  {percent(row.sixMonth)}
                </span>
                <div className="pick-score">
                  <ScoreChange value={row.score} />
                </div>
              </article>
            ))}
            <article className="pick-row pick-summary-row">
              <span className="pick-number" aria-hidden="true" />
              <div className="ticker-block">
                <strong>合計</strong>
              </div>
              <div className="pick-price" aria-hidden="true" />
              <span
                className={`pick-month-to-date ${(averageMonthToDate ?? 0) < 0 ? "negative" : ""}`}
              >
                {percent(averageMonthToDate)}
              </span>
              <span aria-hidden="true" />
              <span aria-hidden="true" />
              <span aria-hidden="true" />
              <div className="pick-score" aria-hidden="true" />
            </article>
          </div>
        </section>
      ) : null}

      <section className="performance-panel">
        <div className="performance-chart">
          <div className="section-heading compact">
            <div>
              <h2>バックテスト資産推移</h2>
            </div>
            <button className="text-button" onClick={() => onNavigate("backtest")}>
              詳細を見る
            </button>
          </div>
          <div className="equity-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid
                  vertical={false}
                  stroke="var(--line)"
                  strokeDasharray="2 4"
                />
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  minTickGap={36}
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  width={46}
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  tickFormatter={(value) => decimal.format(Number(value))}
                />
                <Tooltip content={<EquityTooltip />} />
                <Line
                  type="monotone"
                  dataKey="equity"
                  stroke="var(--accent)"
                  strokeWidth={2.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="stats-column">
          <Metric
            label="最終資産"
            value={`${decimal.format(data.backtest.stats.finalEquity)}x`}
            tone="positive"
          />
          <Metric
            label="CAGR"
            value={percent(data.backtest.stats.cagr)}
            tone="positive"
          />
          <Metric
            label="最大ドローダウン"
            value={percent(data.backtest.stats.maxDrawdown)}
            tone="negative"
          />
          <Metric
            label="年率ボラティリティ"
            value={percent(data.backtest.stats.annualizedVolatility)}
          />
        </div>
      </section>
    </div>
  );
}

function ReturnTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <span>{label}</span>
      <strong>{decimal.format(payload[0].value ?? 0)}%</strong>
    </div>
  );
}

function EquityTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <span>{label}</span>
      <strong>{decimal.format(payload[0].value ?? 0)}</strong>
    </div>
  );
}

function Screener({ data }: { data: DashboardPayload }) {
  const rows = data.momentum;
  const [query, setQuery] = useState("");
  const [onlyEligible, setOnlyEligible] = useState(false);
  const [genre, setGenre] = useState("all");

  const genres = useMemo(
    () => [...new Set(rows.map((row) => row.genre))].sort(),
    [rows],
  );
  const filtered = useMemo(
    () =>
      rows.filter((row) => {
        const matchesQuery =
          !query ||
          row.symbol.toLowerCase().includes(query.toLowerCase()) ||
          row.genre.toLowerCase().includes(query.toLowerCase());
        const matchesEligible = !onlyEligible || row.eligible;
        const matchesGenre = genre === "all" || row.genre === genre;
        return matchesQuery && matchesEligible && matchesGenre;
      }),
    [rows, query, onlyEligible, genre],
  );

  return (
    <div className="view-stack">
      <div className="page-meta-row">
        <div className="summary-count">
          <strong>{decimal.format(filtered.length)}</strong>
          <span>銘柄</span>
        </div>
      </div>

      <div className="filters">
        <label className="search-field">
          <span className="sr-only">銘柄を検索</span>
          <MagnifyingGlassIcon />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ticker またはテーマ"
          />
          {query ? (
            <button onClick={() => setQuery("")} aria-label="検索をクリア">
              <XIcon />
            </button>
          ) : null}
        </label>
        <label className="select-field">
          <span>テーマ</span>
          <select value={genre} onChange={(event) => setGenre(event.target.value)}>
            <option value="all">すべて</option>
            {genres.map((item) => (
              <option value={item} key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="check-filter">
          <input
            type="checkbox"
            checked={onlyEligible}
            onChange={(event) => setOnlyEligible(event.target.checked)}
          />
          <span>Eligibleのみ</span>
        </label>
      </div>

      {filtered.length ? (
        <div className="table-shell analysis-table">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>銘柄</th>
                <th>現在値</th>
                <th>1M</th>
                <th>3M</th>
                <th>6M</th>
                <th>Score</th>
                <th>判定</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.symbol} className={row.selected ? "selected-row" : ""}>
                  <td className="rank-cell" data-label="Rank">
                    {row.rank === null ? <span className="muted">-</span> : row.rank}
                  </td>
                  <td className="ticker-data" data-label="銘柄">
                    <div className="ticker-cell">
                      <strong>{row.symbol}</strong>
                      <span>{row.genre}</span>
                    </div>
                  </td>
                  <td className="numeric current-cell" data-label="現在値">
                    {row.current === null ? "N/A" : `$${decimal.format(row.current)}`}
                  </td>
                  <td
                    className={`numeric return-cell ${(row.oneMonth ?? 0) < 0 ? "negative" : ""}`}
                    data-label="1M"
                  >
                    {percent(row.oneMonth)}
                  </td>
                  <td
                    className={`numeric return-cell ${(row.threeMonth ?? 0) < 0 ? "negative" : ""}`}
                    data-label="3M"
                  >
                    {percent(row.threeMonth)}
                  </td>
                  <td
                    className={`numeric return-cell ${(row.sixMonth ?? 0) < 0 ? "negative" : ""}`}
                    data-label="6M"
                  >
                    {percent(row.sixMonth)}
                  </td>
                  <td className="score-cell" data-label="Score">
                    <ScoreChange value={row.score} />
                  </td>
                  <td className="decision-cell" data-label="判定">
                    <span
                      className={`decision ${row.selected ? "selected" : row.eligible ? "eligible" : "excluded"}`}
                    >
                      {row.reason}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="該当する銘柄がありません"
          body="検索条件またはテーマの絞り込みを変更してください。"
        />
      )}

    </div>
  );
}

function PortfolioView({
  data,
  holdings,
  onHoldingChange,
}: {
  data: DashboardPayload;
  holdings: HoldingMap;
  onHoldingChange: (symbol: string, value: number) => void;
}) {
  const allocationIsCash = data.market.allocationStatus !== "Invest";
  const insufficient =
    data.market.allocationStatus === "CashInsufficient";
  const rows = data.portfolio.map((row) => {
    const actualShares = holdings[row.symbol] ?? 0;
    const actualAmount = actualShares * (row.current ?? 0);
    return {
      ...row,
      actualShares,
      actualAmount,
      difference: actualAmount - row.targetAmount,
    };
  });
  const targetTotal = rows.reduce((sum, row) => sum + row.targetAmount, 0);
  const actualTotal = rows.reduce((sum, row) => sum + row.actualAmount, 0);
  const difference = actualTotal - targetTotal;

  return (
    <div className="view-stack">
      <section
        className={`portfolio-summary${allocationIsCash ? "" : " invested"}`}
      >
        {allocationIsCash ? (
          <>
            <Metric label="目標総額" value="$0" />
            <Metric label="採用銘柄" value="0" />
            <Metric label="現金比率" value="100%" tone="positive" />
            <Metric
              label="判定理由"
              value={insufficient ? "候補不足" : "市場Cash"}
              detail={
                insufficient
                  ? `${decimal.format(data.market.selectedCount)}/${decimal.format(data.config.topN)}銘柄`
                  : "QQQ 10M MA"
              }
            />
          </>
        ) : (
          <>
            <Metric
              label="目標総額"
              value={`$${money.format(targetTotal)}`}
              detail={`¥${money.format(targetTotal * data.config.usdJpy)}`}
            />
            <Metric
              label="現在評価額"
              value={`$${money.format(actualTotal)}`}
              detail={`¥${money.format(actualTotal * data.config.usdJpy)}`}
              tone={actualTotal > 0 ? "positive" : "neutral"}
            />
            <Metric
              label="調整差額"
              value={`${difference >= 0 ? "+" : ""}$${money.format(difference)}`}
              detail={`${difference >= 0 ? "+" : ""}¥${money.format(difference * data.config.usdJpy)}`}
              tone={difference >= 0 ? "positive" : "negative"}
            />
          </>
        )}
      </section>

      {allocationIsCash ? (
        <EmptyState
          title="今月は全額現金です"
          body={
            insufficient
              ? `採用候補が${decimal.format(data.market.selectedCount)}銘柄のため、目標の${decimal.format(data.config.topN)}銘柄を満たしていません。`
              : "QQQが10か月移動平均以下のため、配分を停止しています。"
          }
        />
      ) : (
        <div className="table-shell portfolio-table">
          <table>
          <thead>
            <tr>
              <th>銘柄</th>
              <th>現在値</th>
              <th>目標額</th>
              <th>目標株数</th>
              <th>実保有株数</th>
              <th>現在評価額</th>
              <th>差額</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.symbol}>
                <td className="ticker-data" data-label="銘柄">
                  <div className="ticker-cell">
                    <strong>{row.symbol}</strong>
                    <span>{row.genre}</span>
                  </div>
                </td>
                <td className="numeric" data-label="現在値">
                  {row.current === null ? (
                    "N/A"
                  ) : (
                    <span className="currency-pair">
                      <span>${decimal.format(row.current)}</span>
                      <small>
                        ¥{money.format(row.current * data.config.usdJpy)}
                      </small>
                    </span>
                  )}
                </td>
                <td className="numeric" data-label="目標額">
                  <span className="currency-pair">
                    <span>${money.format(row.targetAmount)}</span>
                    <small>
                      ¥{money.format(row.targetAmount * data.config.usdJpy)}
                    </small>
                  </span>
                </td>
                <td className="numeric" data-label="目標株数">
                  {row.targetShares === null
                    ? "N/A"
                    : decimal.format(row.targetShares)}
                </td>
                <td data-label="実保有株数">
                  <label className="inline-number">
                    <span className="sr-only">{row.symbol}の保有株数</span>
                    <FormattedNumberInput
                      ariaLabel={`${row.symbol}の保有株数`}
                      min={0}
                      max={1000000000}
                      maximumFractionDigits={3}
                      value={row.actualShares}
                      placeholder="0"
                      emptyWhenZero
                      onChange={(value) => onHoldingChange(row.symbol, value)}
                    />
                  </label>
                </td>
                <td className="numeric" data-label="現在評価額">
                  <span className="currency-pair">
                    <span>${money.format(row.actualAmount)}</span>
                    <small>
                      ¥{money.format(row.actualAmount * data.config.usdJpy)}
                    </small>
                  </span>
                </td>
                <td
                  className={`numeric difference ${row.difference >= 0 ? "positive" : "negative"}`}
                  data-label="差額"
                >
                  <span className="currency-pair">
                    <span>
                      {row.difference >= 0 ? "+" : ""}$
                      {money.format(row.difference)}
                    </span>
                    <small>
                      {row.difference >= 0 ? "+" : ""}¥
                      {money.format(row.difference * data.config.usdJpy)}
                    </small>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>
      )}
      <p className="fine-print">
        保有株数はこのブラウザ内だけに保存されます。売買注文は送信されません。
      </p>
    </div>
  );
}

function BacktestView({ data }: { data: DashboardPayload }) {
  const [showAll, setShowAll] = useState(false);
  const rows = showAll ? data.backtest.rows : data.backtest.rows.slice(-12);
  const chartData = data.backtest.rows
    .filter((row) => typeof row.equity === "number")
    .map((row) => ({
      date: row.signalMonth.slice(0, 7),
      equity: (row.equity ?? 1) * 100,
      monthly: (row.monthlyReturn ?? 0) * 100,
    }));

  return (
    <div className="view-stack">
      <div className="page-meta-row">
        <div className="date-range">
          {data.config.backtestStart.replaceAll("-", ".")} - 最新
        </div>
      </div>

      <section className="backtest-stats">
        <Metric
          label="最終資産"
          value={`${decimal.format(data.backtest.stats.finalEquity)}x`}
          tone="positive"
        />
        <Metric
          label="CAGR"
          value={percent(data.backtest.stats.cagr)}
          tone="positive"
        />
        <Metric
          label="月次平均"
          value={percent(data.backtest.stats.averageMonthlyReturn)}
          tone="positive"
        />
        <Metric
          label="最大DD"
          value={percent(data.backtest.stats.maxDrawdown)}
          tone="negative"
        />
        <Metric
          label="年率Vol"
          value={percent(data.backtest.stats.annualizedVolatility)}
        />
      </section>

      <section className="large-chart-panel">
        <div className="section-heading compact">
          <div>
            <h2>資産曲線</h2>
          </div>
        </div>
        <div className="large-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid
                vertical={false}
                stroke="var(--line)"
                strokeDasharray="2 4"
              />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                minTickGap={42}
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                width={52}
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickFormatter={(value) => decimal.format(Number(value))}
              />
              <Tooltip content={<EquityTooltip />} />
              <Line
                type="monotone"
                dataKey="equity"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <h2>月次シグナル</h2>
            <p>
              月末判定後の翌営業日に約定し、翌月末の翌営業日に決済
            </p>
          </div>
          <button className="text-button" onClick={() => setShowAll(!showAll)}>
            {showAll ? "直近12か月" : "全期間を表示"}
          </button>
        </div>
        <div className="table-shell backtest-table">
          <table>
            <thead>
              <tr>
                <th>シグナル月</th>
                <th>市場</th>
                <th>採用銘柄</th>
                <th>月次</th>
                <th>資産</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <BacktestTableRow row={row} key={row.signalMonth} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function BacktestTableRow({ row }: { row: BacktestRow }) {
  return (
    <tr>
      <td className="numeric" data-label="シグナル月">
        {compactDate(row.signalMonth)}
      </td>
      <td data-label="市場">
        <span
          className={`market-tag ${row.market === "RiskOn" ? "risk-on" : "cash"}`}
        >
          {row.market}
        </span>
      </td>
      <td className="picks-cell" data-label="採用銘柄">
        {row.picks.length ? (
          <div className="ticker-list">
            {row.picks.map((pick) => (
              <span key={pick}>{pick}</span>
            ))}
          </div>
        ) : (
          <span className="muted">配分なし</span>
        )}
      </td>
      <td
        className={`numeric ${(row.monthlyReturn ?? 0) < 0 ? "negative" : "positive"}`}
        data-label="月次"
      >
        {row.provisional ? "暫定" : percent(row.monthlyReturn)}
      </td>
      <td className="numeric" data-label="資産">
        {row.equity === null ? "暫定" : `${decimal.format(row.equity)}x`}
      </td>
    </tr>
  );
}

function SettingsView({
  config,
  loading,
  onApply,
}: {
  config: StrategyConfig;
  loading: boolean;
  onApply: (config: StrategyConfig) => void;
}) {
  const [draft, setDraft] = useState(config);
  useEffect(() => setDraft(config), [config]);

  function updateWeight(key: keyof StrategyConfig["weights"], value: number) {
    setDraft((current) => ({
      ...current,
      weights: { ...current.weights, [key]: value },
    }));
  }

  const weightTotal =
    draft.weights.oneMonth +
    draft.weights.threeMonth +
    draft.weights.sixMonth;
  const isValid = Math.abs(weightTotal - 1) < 0.001;
  const derivedTargetAmountUsd = getTargetAmountUsd(draft);

  return (
    <div className="view-stack">
      <form
        className="settings-grid"
        onSubmit={(event) => {
          event.preventDefault();
        }}
      >
        <section className="setting-section">
          <div className="setting-heading">
            <SlidersHorizontalIcon size={22} />
            <div>
              <h2>スコア配分</h2>
              <p>1M、3M、6Mの加重平均</p>
            </div>
          </div>
          <div className="form-grid three">
            <NumberField
              label="1か月"
              value={draft.weights.oneMonth}
              step={0.05}
              min={0}
              max={1}
              suffix="%"
              displayMultiplier={100}
              onChange={(value) => updateWeight("oneMonth", value)}
            />
            <NumberField
              label="3か月"
              value={draft.weights.threeMonth}
              step={0.05}
              min={0}
              max={1}
              suffix="%"
              displayMultiplier={100}
              onChange={(value) => updateWeight("threeMonth", value)}
            />
            <NumberField
              label="6か月"
              value={draft.weights.sixMonth}
              step={0.05}
              min={0}
              max={1}
              suffix="%"
              displayMultiplier={100}
              onChange={(value) => updateWeight("sixMonth", value)}
            />
          </div>
          <div className={`weight-total ${isValid ? "valid" : "invalid"}`}>
            <span>合計</span>
            <strong>{Math.round(weightTotal * 100)}%</strong>
            <small>
              {isValid ? "適用できます" : "合計を100%にしてください"}
            </small>
          </div>
        </section>

        <section className="setting-section">
          <div className="setting-heading">
            <TargetIcon size={22} />
            <div>
              <h2>選定条件</h2>
              <p>採用数と過熱除外の基準</p>
            </div>
          </div>
          <div className="form-grid two">
            <NumberField
              label="採用銘柄数"
              value={draft.topN}
              step={1}
              min={1}
              max={20}
              onChange={(value) =>
                setDraft((current) => ({ ...current, topN: value }))
              }
            />
            <NumberField
              label="1か月急騰除外"
              value={draft.surgeLimit}
              step={0.05}
              min={0.1}
              max={5}
              suffix="%"
              displayMultiplier={100}
              onChange={(value) =>
                setDraft((current) => ({ ...current, surgeLimit: value }))
              }
            />
            <NumberField
              label="QQQ移動平均"
              value={draft.qqqMaMonths}
              step={1}
              min={3}
              max={24}
              suffix="か月"
              onChange={(value) =>
                setDraft((current) => ({ ...current, qqqMaMonths: value }))
              }
            />
            <NumberField
              label="Frontier上限"
              value={draft.frontierMax}
              step={1}
              min={0}
              max={20}
              suffix="銘柄"
              onChange={(value) =>
                setDraft((current) => ({ ...current, frontierMax: value }))
              }
            />
          </div>
        </section>

        <section className="setting-section span-full">
          <div className="setting-heading">
            <ListChecksIcon size={22} />
            <div>
              <h2>テーマ上限と除外</h2>
              <p>同一テーマへの集中と個別銘柄を制御</p>
            </div>
          </div>
          <div className="form-grid three">
            <NumberField
              label="Genre共通上限"
              value={draft.genreMax}
              step={1}
              min={1}
              max={20}
              suffix="銘柄"
              onChange={(value) =>
                setDraft((current) => ({ ...current, genreMax: value }))
              }
            />
          </div>
          <label className="field excluded-field">
            <span>除外Ticker</span>
            <div className="input-wrap">
              <input
                type="text"
                value={draft.excludedTickers.join(", ")}
                placeholder="例: TQQQ, SOXL"
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    excludedTickers: event.target.value
                      .split(",")
                      .map((value) => value.trim().toUpperCase())
                      .filter(Boolean),
                  }))
                }
              />
            </div>
          </label>
        </section>

        <section className="setting-section span-full">
          <div className="setting-heading">
            <WalletIcon size={22} />
            <div>
              <h2>配分と換算</h2>
              <p>合計の円建て目標額から1銘柄のドル額を自動算出</p>
            </div>
          </div>
          <div className="form-grid three">
            <NumberField
              label="合計の目標額"
              value={draft.targetTotalJpy}
              step={10000}
              min={10000}
              max={1000000000}
              prefix="¥"
              onChange={(value) =>
                setDraft((current) => ({
                  ...current,
                  targetTotalJpy: value,
                }))
              }
            />
            <label className="field">
              <span>1銘柄の目標額（自動）</span>
              <div className="input-wrap readonly">
                <i>$</i>
                <input
                  type="text"
                  value={decimal.format(derivedTargetAmountUsd)}
                  readOnly
                  aria-label="1銘柄のドル建て目標額"
                />
              </div>
            </label>
            <NumberField
              label="USD / JPY"
              value={draft.usdJpy}
              step={0.01}
              min={1}
              max={1000}
              prefix="¥"
              onChange={(value) =>
                setDraft((current) => ({ ...current, usdJpy: value }))
              }
            />
            <label className="field">
              <span>バックテスト開始日</span>
              <div className="input-wrap">
                <input
                  type="date"
                  value={draft.backtestStart}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      backtestStart: event.target.value,
                    }))
                  }
                />
              </div>
            </label>
          </div>
        </section>

        <OperationScheduleSection />

        <div className="settings-actions span-full">
          <p>
            設定を適用すると、公開済みの価格履歴から全シグナルを再計算します。
          </p>
          <button
            className="primary-button"
            type="button"
            disabled={!isValid || loading}
            onClick={() => {
              if (
                isValid &&
                window.confirm(
                  "この設定を適用しますか？\n全シグナルとバックテスト結果を再計算します。",
                )
              ) {
                onApply(draft);
              }
            }}
          >
            {loading ? <LoadingLine /> : <ArrowClockwiseIcon />}
            {loading ? "再計算中" : "設定を適用"}
          </button>
        </div>
      </form>
    </div>
  );
}

function FormattedNumberInput({
  value,
  onChange,
  min,
  max,
  maximumFractionDigits = 4,
  placeholder,
  ariaLabel,
  emptyWhenZero = false,
}: {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  maximumFractionDigits?: number;
  placeholder?: string;
  ariaLabel?: string;
  emptyWhenZero?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  const [editingValue, setEditingValue] = useState("");
  const formatter = useMemo(
    () =>
      new Intl.NumberFormat("ja-JP", {
        maximumFractionDigits,
        useGrouping: true,
      }),
    [maximumFractionDigits],
  );
  const plainValue = Number(value.toFixed(maximumFractionDigits)).toString();
  const formattedValue =
    emptyWhenZero && value === 0 ? "" : formatter.format(value);

  return (
    <input
      type="text"
      role="spinbutton"
      inputMode="decimal"
      value={focused ? editingValue : formattedValue}
      placeholder={placeholder}
      aria-label={ariaLabel}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      onFocus={() => {
        setEditingValue(emptyWhenZero && value === 0 ? "" : plainValue);
        setFocused(true);
      }}
      onChange={(event) => {
        const raw = event.target.value.replaceAll(",", "");
        setEditingValue(raw);
        if (raw.trim() === "") return;
        const parsed = Number(raw);
        if (Number.isFinite(parsed)) onChange(parsed);
      }}
      onBlur={() => {
        const parsed = Number(editingValue.replaceAll(",", ""));
        const next = Number.isFinite(parsed) ? parsed : value;
        onChange(Math.min(max, Math.max(min, next)));
        setFocused(false);
      }}
    />
  );
}

function NumberField({
  label,
  value,
  onChange,
  prefix,
  suffix,
  displayMultiplier = 1,
  ...inputProps
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  prefix?: string;
  suffix?: string;
  displayMultiplier?: number;
  step: number;
  min: number;
  max: number;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <div className="input-wrap">
        {prefix ? <i>{prefix}</i> : null}
        <FormattedNumberInput
          value={value * displayMultiplier}
          onChange={(next) => onChange(next / displayMultiplier)}
          min={inputProps.min * displayMultiplier}
          max={inputProps.max * displayMultiplier}
          maximumFractionDigits={4}
        />
        {suffix ? <i>{suffix}</i> : null}
      </div>
    </label>
  );
}

export function MomentumApp({
  initialDashboard,
}: {
  initialDashboard: DashboardPayload;
}) {
  const [view, setView] = useState<View>("overview");
  const [data, setData] = useState<DashboardPayload>(initialDashboard);
  const [config, setConfig] = useState<StrategyConfig>(
    normalizeStrategyConfig(initialDashboard.config),
  );
  const [holdings, setHoldings] = useState<HoldingMap>({});
  const [histories, setHistories] = useState<Record<string, PricePoint[]> | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const didInitialLoad = useRef(false);

  useEffect(() => {
    const savedHoldings = window.localStorage.getItem("momentum-holdings");
    if (savedHoldings) {
      try {
        setHoldings(JSON.parse(savedHoldings) as HoldingMap);
      } catch {
        window.localStorage.removeItem("momentum-holdings");
      }
    }
  }, []);

  const refresh = useCallback(async (
    strategy: StrategyConfig,
    forceDownload = false,
  ) => {
    setLoading(true);
    try {
      const normalizedStrategy = normalizeStrategyConfig(strategy);
      let nextHistories = histories;
      let refreshWarnings: string[] = [];
      if (!nextHistories || forceDownload) {
        const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
        const response = await fetch(
          `${basePath}/data/market-data.json?ts=${Date.now()}`,
          { cache: "no-store" },
        );
        if (!response.ok) throw new Error("公開データの取得に失敗しました。");
        const marketData = (await response.json()) as MarketDataFile;
        nextHistories = marketData.histories;
      }

      if (forceDownload) {
        const live = await fetchYahooHistoriesInBrowser(
          [...TICKERS.map((ticker) => ticker.symbol), USD_JPY_SYMBOL],
        );
        nextHistories = mergeHistories(nextHistories, live.histories);
        refreshWarnings = live.errors;
      }

      const nextStrategy = withLatestUsdJpy(
        normalizedStrategy,
        nextHistories,
      );
      const payload = buildDashboard(nextHistories, TICKERS, nextStrategy);
      if (refreshWarnings.length) {
        payload.warning =
          `一部銘柄の最新価格を取得できませんでした（${decimal.format(refreshWarnings.length)}件）。` +
          "取得済みの価格で計算しています。";
      }
      setHistories(nextHistories);
      setData(payload);
      setConfig(nextStrategy);
      window.localStorage.setItem(
        STRATEGY_STORAGE_KEY,
        JSON.stringify(nextStrategy),
      );
    } catch (error) {
      setData((current) => ({
        ...current,
        warning:
          error instanceof Error
            ? error.message
            : "データ更新に失敗しました。",
      }));
    } finally {
      setLoading(false);
    }
  }, [histories]);

  const refreshUsdJpy = useCallback(async () => {
    try {
      const points = await fetchYahooHistoryInBrowser(USD_JPY_SYMBOL);
      const latest = points.at(-1)?.close;
      if (
        typeof latest !== "number" ||
        !Number.isFinite(latest) ||
        latest <= 0
      ) {
        return;
      }
      setHistories((current) =>
        current
          ? mergeHistories(current, { [USD_JPY_SYMBOL]: points })
          : current,
      );
      setConfig((current) => {
        const next = normalizeStrategyConfig({ ...current, usdJpy: latest });
        window.localStorage.setItem(STRATEGY_STORAGE_KEY, JSON.stringify(next));
        return next;
      });
      setData((current) => {
        const nextConfig = normalizeStrategyConfig({
          ...current.config,
          usdJpy: latest,
        });
        const targetAmount = getTargetAmountUsd(nextConfig);
        return {
          ...current,
          config: nextConfig,
          portfolio: current.portfolio.map((row) => ({
            ...row,
            targetAmount,
            targetShares:
              row.current && row.current > 0
                ? targetAmount / row.current
                : null,
          })),
        };
      });
    } catch {
      // Keep the most recently acquired rate when a periodic refresh fails.
    }
  }, []);

  useEffect(() => {
    if (didInitialLoad.current) return;
    didInitialLoad.current = true;

    const savedConfig = window.localStorage.getItem(STRATEGY_STORAGE_KEY);
    if (savedConfig) {
      try {
        const savedVersion = window.localStorage.getItem(
          STRATEGY_STORAGE_VERSION_KEY,
        );
        const stored = JSON.parse(savedConfig) as StrategyConfig;
        const parsed = normalizeStrategyConfig(
          savedVersion === STRATEGY_STORAGE_VERSION
            ? stored
            : {
                ...stored,
                topN: DEFAULT_STRATEGY.topN,
                weights: { ...DEFAULT_STRATEGY.weights },
                genreMax: DEFAULT_STRATEGY.genreMax,
                frontierMax: DEFAULT_STRATEGY.frontierMax,
              },
        );
        window.localStorage.setItem(
          STRATEGY_STORAGE_KEY,
          JSON.stringify(parsed),
        );
        window.localStorage.setItem(
          STRATEGY_STORAGE_VERSION_KEY,
          STRATEGY_STORAGE_VERSION,
        );
        setConfig(parsed);
        void refresh(parsed);
        return;
      } catch {
        window.localStorage.removeItem(STRATEGY_STORAGE_KEY);
        window.localStorage.removeItem(STRATEGY_STORAGE_VERSION_KEY);
      }
    }
    window.localStorage.setItem(
      STRATEGY_STORAGE_VERSION_KEY,
      STRATEGY_STORAGE_VERSION,
    );
    void refresh(initialDashboard.config);
  }, [initialDashboard.config, refresh]);

  useEffect(() => {
    void refreshUsdJpy();
    const interval = window.setInterval(
      () => void refreshUsdJpy(),
      USD_JPY_REFRESH_INTERVAL_MS,
    );
    return () => window.clearInterval(interval);
  }, [refreshUsdJpy]);

  function changeView(next: View) {
    setView(next);
    setMobileNavOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function updateHolding(symbol: string, value: number) {
    const next = { ...holdings, [symbol]: value };
    setHoldings(next);
    window.localStorage.setItem("momentum-holdings", JSON.stringify(next));
  }

  const activeLabel = views.find((item) => item.id === view)?.label ?? "概要";

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-terminal">
            <strong>MOMENTUM CONSOLE</strong>
            <span>OPERATIONAL TERMINAL</span>
          </div>
        </div>
        <nav aria-label="メインナビゲーション">
          {views.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={view === item.id ? "active" : ""}
                onClick={() => changeView(item.id)}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      {mobileNavOpen ? (
        <button
          className="nav-scrim"
          aria-label="メニューを閉じる"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}

      <main>
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileNavOpen(true)}
            aria-label="メニューを開く"
          >
            <SlidersHorizontalIcon />
          </button>
          <div className="terminal-meta">
            <span>DATA: EOD {compactDate(data.asOf)}</span>
            <span>USD/JPY: {decimal.format(config.usdJpy)}</span>
          </div>
          <div className="topbar-actions">
            <SourceBadge payload={data} />
            <button
              className="refresh-button"
              onClick={() => void refresh(config, true)}
              disabled={loading}
              aria-label={loading ? "価格を更新中" : "価格を更新"}
            >
              {loading ? <LoadingLine /> : <ArrowClockwiseIcon />}
              <span>{loading ? "更新中" : "価格を更新"}</span>
            </button>
          </div>
        </header>

        <div className="workspace-header">
          <strong>{activeLabel}</strong>
        </div>

        <div className="content">
          {view === "overview" ? (
            <Overview data={data} loading={loading} onNavigate={changeView} />
          ) : null}
          {view === "screener" ? <Screener data={data} /> : null}
          {view === "portfolio" ? (
            <PortfolioView
              data={data}
              holdings={holdings}
              onHoldingChange={updateHolding}
            />
          ) : null}
          {view === "backtest" ? <BacktestView data={data} /> : null}
          {view === "comparison" ? (
            <CandidateManagerView data={data} />
          ) : null}
          {view === "settings" ? (
            <SettingsView
              config={config}
              loading={loading}
              onApply={(next) => void refresh(next)}
            />
          ) : null}
        </div>
      </main>
    </div>
  );
}
