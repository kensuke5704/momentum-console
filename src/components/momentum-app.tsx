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
  BinocularsIcon,
  ScalesIcon,
  SlidersHorizontalIcon,
  TargetIcon,
  TrendDownIcon,
  TrendUpIcon,
  WarningCircleIcon,
  WalletIcon,
  XIcon,
} from "@phosphor-icons/react";
import {
  Area,
  AreaChart,
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
import { TICKERS } from "@/lib/config";
import { buildDashboard } from "@/lib/momentum";
import { ComparisonView } from "@/components/comparison-view";
import { ResearchView } from "@/components/research-view";
import { fetchYahooHistoriesInBrowser } from "@/lib/yahoo-client";
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
  | "research"
  | "comparison"
  | "settings";
type HoldingMap = Record<string, number>;
type MarketDataFile = {
  generatedAt: string;
  histories: Record<string, PricePoint[]>;
  dashboard: DashboardPayload;
};

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
  { id: "research", label: "調査", icon: BinocularsIcon },
  { id: "comparison", label: "候補比較", icon: ScalesIcon },
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

  return (
    <div className="view-stack">
      {data.warning ? (
        <div className="warning-banner" role="status">
          <WarningCircleIcon size={20} weight="fill" />
          <span>{data.warning}</span>
        </div>
      ) : null}

      <section className="market-panel">
        <div className="market-copy">
          <div className="section-label">現在の配分判定</div>
          <div className="market-state-row">
            <div
              className={`market-icon ${allocationIsCash ? "cash" : "risk-on"}`}
            >
              {allocationIsCash ? (
                <TrendDownIcon weight="bold" />
              ) : (
                <TrendUpIcon weight="bold" />
              )}
            </div>
            <div>
              <h1>{allocationLabel}</h1>
              <p>
                {insufficient
                  ? `QQQはRiskOnですが、採用候補が${data.market.selectedCount}/${data.config.topN}銘柄のため、ルールにより全額現金です。`
                  : data.market.state === "RiskOn"
                    ? "QQQは10か月移動平均を上回っています。選定銘柄への配分シグナルです。"
                    : "QQQは10か月移動平均以下です。新規配分を停止するシグナルです。"}
              </p>
              <p className="decision-date">
                判定基準日 {compactDate(data.market.decisionDate)}（確定月末）
              </p>
            </div>
          </div>
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
        <section>
          <div className="section-heading">
            <div>
              <h2>今月の採用銘柄</h2>
              <p>
                相対モメンタムとテーマ上限を通過した
                {data.portfolio.length}銘柄
              </p>
            </div>
            <button className="text-button" onClick={() => onNavigate("portfolio")}>
              配分を確認
              <ArrowUpIcon className="arrow-right" />
            </button>
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
                  <span>現在値</span>
                  <strong>
                    {row.current === null ? "N/A" : `$${decimal.format(row.current)}`}
                  </strong>
                </div>
                <div className="pick-score">
                  <span>Score</span>
                  <ScoreChange value={row.score} />
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="performance-panel">
        <div className="performance-chart">
          <div className="section-heading compact">
            <div>
              <h2>バックテスト資産推移</h2>
              <p>初期資産を100として表示</p>
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
      <div className="page-intro">
        <div>
          <h1>銘柄分析</h1>
          <p>
            モメンタム、QQQ比較、テーマ制限を一つの表で確認できます。
          </p>
        </div>
        <div className="summary-count">
          <strong>{filtered.length}</strong>
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
        <div className="table-shell">
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
                  <td className="rank-cell">
                    {row.rank === null ? <span className="muted">-</span> : row.rank}
                  </td>
                  <td>
                    <div className="ticker-cell">
                      <strong>{row.symbol}</strong>
                      <span>{row.genre}</span>
                    </div>
                  </td>
                  <td className="numeric">
                    {row.current === null ? "N/A" : `$${decimal.format(row.current)}`}
                  </td>
                  <td className={`numeric ${(row.oneMonth ?? 0) < 0 ? "negative" : ""}`}>
                    {percent(row.oneMonth)}
                  </td>
                  <td className={`numeric ${(row.threeMonth ?? 0) < 0 ? "negative" : ""}`}>
                    {percent(row.threeMonth)}
                  </td>
                  <td className={`numeric ${(row.sixMonth ?? 0) < 0 ? "negative" : ""}`}>
                    {percent(row.sixMonth)}
                  </td>
                  <td>
                    <ScoreChange value={row.score} />
                  </td>
                  <td>
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
      <div className="page-intro">
        <div>
          <h1>ポートフォリオ</h1>
          <p>
            {allocationIsCash
              ? "今月は全額現金です。新規の買付配分はありません。"
              : "実際の保有株数を入力すると、目標配分との差額を自動計算します。"}
          </p>
        </div>
      </div>

      <section className="portfolio-summary">
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
                  ? `${data.market.selectedCount}/${data.config.topN}銘柄`
                  : "QQQ 10M MA"
              }
            />
          </>
        ) : (
          <>
            <Metric label="目標総額" value={`$${money.format(targetTotal)}`} />
            <Metric
              label="現在評価額"
              value={`$${money.format(actualTotal)}`}
              tone={actualTotal > 0 ? "positive" : "neutral"}
            />
            <Metric
              label="調整差額"
              value={`${difference >= 0 ? "+" : ""}$${money.format(difference)}`}
              tone={difference >= 0 ? "positive" : "negative"}
            />
            <Metric
              label="円換算"
              value={`¥${money.format(actualTotal * data.config.usdJpy)}`}
              detail={`USD/JPY ${decimal.format(data.config.usdJpy)}`}
            />
          </>
        )}
      </section>

      {allocationIsCash ? (
        <EmptyState
          title="今月は全額現金です"
          body={
            insufficient
              ? `採用候補が${data.market.selectedCount}銘柄のため、目標の${data.config.topN}銘柄を満たしていません。`
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
                <td>
                  <div className="ticker-cell">
                    <strong>{row.symbol}</strong>
                    <span>{row.genre}</span>
                  </div>
                </td>
                <td className="numeric">
                  {row.current === null ? "N/A" : `$${decimal.format(row.current)}`}
                </td>
                <td className="numeric">${money.format(row.targetAmount)}</td>
                <td className="numeric">
                  {row.targetShares === null
                    ? "N/A"
                    : decimal.format(row.targetShares)}
                </td>
                <td>
                  <label className="inline-number">
                    <span className="sr-only">{row.symbol}の保有株数</span>
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={row.actualShares || ""}
                      placeholder="0"
                      onChange={(event) =>
                        onHoldingChange(
                          row.symbol,
                          Math.max(0, Number(event.target.value) || 0),
                        )
                      }
                    />
                  </label>
                </td>
                <td className="numeric">${money.format(row.actualAmount)}</td>
                <td
                  className={`numeric difference ${row.difference >= 0 ? "positive" : "negative"}`}
                >
                  {row.difference >= 0 ? "+" : ""}$
                  {money.format(row.difference)}
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
      <div className="page-intro">
        <div>
          <h1>バックテスト</h1>
          <p>
            月末シグナル、3日後の約定、翌月3日後の決済で検証します。
          </p>
        </div>
        <div className="date-range">
          {data.config.backtestStart.replaceAll("-", ".")} - 最新
        </div>
      </div>

      <section className="backtest-stats">
        <Metric
          label="最終資産"
          value={`${decimal.format(data.backtest.stats.finalEquity)}x`}
          detail="初期資産 1.00"
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
            <p>初期資産を100として指数化</p>
          </div>
        </div>
        <div className="large-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="equityFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
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
              />
              <Tooltip content={<EquityTooltip />} />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="var(--accent)"
                strokeWidth={2.5}
                fill="url(#equityFill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <h2>月次シグナル</h2>
            <p>採用銘柄と実績リターン</p>
          </div>
          <button className="text-button" onClick={() => setShowAll(!showAll)}>
            {showAll ? "直近12か月" : "全期間を表示"}
          </button>
        </div>
        <div className="table-shell">
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
      <td className="numeric">{compactDate(row.signalMonth)}</td>
      <td>
        <span
          className={`market-tag ${row.market === "RiskOn" ? "risk-on" : "cash"}`}
        >
          {row.market}
        </span>
      </td>
      <td>
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
      >
        {row.provisional ? "暫定" : percent(row.monthlyReturn)}
      </td>
      <td className="numeric">
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

  return (
    <div className="view-stack">
      <div className="page-intro">
        <div>
          <h1>戦略設定</h1>
          <p>
            Apps Script本番版の条件を初期値として移植しています。
          </p>
        </div>
      </div>

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
            {["Quantum", "AI Semi", "Space"].map((genre) => (
              <NumberField
                key={genre}
                label={`${genre} 上限`}
                value={draft.genreLimits[genre] ?? 0}
                step={1}
                min={0}
                max={20}
                suffix="銘柄"
                onChange={(value) =>
                  setDraft((current) => ({
                    ...current,
                    genreLimits: {
                      ...current.genreLimits,
                      [genre]: value,
                    },
                  }))
                }
              />
            ))}
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
              <p>1銘柄の目標額と参考為替</p>
            </div>
          </div>
          <div className="form-grid three">
            <NumberField
              label="1銘柄の目標額"
              value={draft.targetAmountUsd}
              step={50}
              min={1}
              max={1000000}
              prefix="$"
              onChange={(value) =>
                setDraft((current) => ({
                  ...current,
                  targetAmountUsd: value,
                }))
              }
            />
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

        <div className="settings-actions span-full">
          <p>
            設定を適用すると、公開済みの価格履歴から全シグナルを再計算します。
          </p>
          <button
            className="primary-button"
            type="button"
            disabled={!isValid || loading}
            onClick={() => {
              if (isValid) onApply(draft);
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
        <input
          type="number"
          value={Number((value * displayMultiplier).toFixed(4))}
          onChange={(event) =>
            onChange(Number(event.target.value) / displayMultiplier)
          }
          step={inputProps.step * displayMultiplier}
          min={inputProps.min * displayMultiplier}
          max={inputProps.max * displayMultiplier}
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
    initialDashboard.config,
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
          TICKERS.map((ticker) => ticker.symbol),
        );
        nextHistories = mergeHistories(nextHistories, live.histories);
        refreshWarnings = live.errors;
      }

      const payload = buildDashboard(nextHistories, TICKERS, strategy);
      if (refreshWarnings.length) {
        payload.warning =
          `一部銘柄の最新価格を取得できませんでした（${refreshWarnings.length}件）。` +
          "取得済みの価格で計算しています。";
      }
      setHistories(nextHistories);
      setData(payload);
      setConfig(strategy);
      window.localStorage.setItem(
        "momentum-strategy",
        JSON.stringify(strategy),
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

  useEffect(() => {
    if (didInitialLoad.current) return;
    didInitialLoad.current = true;

    const savedConfig = window.localStorage.getItem("momentum-strategy");
    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig) as StrategyConfig;
        setConfig(parsed);
        void refresh(parsed);
        return;
      } catch {
        window.localStorage.removeItem("momentum-strategy");
      }
    }
    void refresh(initialDashboard.config);
  }, [initialDashboard.config, refresh]);

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
          <div className="brand-mark">
            <ChartLineUpIcon weight="bold" />
          </div>
          <div>
            <strong>Momentum</strong>
            <span>Console</span>
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
        <div className="sidebar-foot">
          <SourceBadge payload={data} />
          <p>データ基準日</p>
          <strong>{compactDate(data.asOf)}</strong>
        </div>
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
          <div>
            <span>Momentum Console</span>
            <strong>{activeLabel}</strong>
          </div>
          <div className="topbar-actions">
            <SourceBadge payload={data} />
            <button
              className="refresh-button"
              onClick={() => void refresh(config, true)}
              disabled={loading}
            >
              {loading ? <LoadingLine /> : <ArrowClockwiseIcon />}
              <span>{loading ? "更新中" : "価格を更新"}</span>
            </button>
          </div>
        </header>

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
          {view === "research" ? <ResearchView data={data} /> : null}
          {view === "comparison" ? (
            <ComparisonView
              data={data}
              histories={histories}
              loading={loading}
              onLoadData={() => void refresh(config, true)}
            />
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
