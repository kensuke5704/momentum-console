"use client";

import {
  ArrowCounterClockwiseIcon,
  CheckCircleIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ScalesIcon,
  TrashIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TICKERS } from "@/lib/config";
import { buildDashboard } from "@/lib/momentum";
import { MaintenancePanel } from "@/components/maintenance-panel";
import type {
  DashboardPayload,
  PricePoint,
  TickerConfig,
} from "@/lib/types";
import { fetchYahooHistoryInBrowser } from "@/lib/yahoo-client";

type CustomTicker = {
  symbol: string;
  status: "loading" | "ready" | "error";
  history?: PricePoint[];
  error?: string;
};

type ComparisonViewProps = {
  data: DashboardPayload;
  histories: Record<string, PricePoint[]> | null;
  loading: boolean;
  onLoadData: () => void;
};

const number = new Intl.NumberFormat("ja-JP", {
  maximumFractionDigits: 2,
});

function percent(value: number | null, digits = 1) {
  if (value === null || !Number.isFinite(value)) return "N/A";
  return `${(value * 100).toFixed(digits)}%`;
}

function signed(value: number, suffix: string, digits = 1) {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}${suffix}`;
}

function normalizeSymbol(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}

function baselineUniverse(data: DashboardPayload) {
  const excluded = new Set(
    data.config.excludedTickers.map((symbol) => symbol.toUpperCase()),
  );
  return new Set(
    TICKERS.filter(
      (ticker) => ticker.symbol !== "QQQ" && !excluded.has(ticker.symbol),
    ).map((ticker) => ticker.symbol),
  );
}

function Delta({
  value,
  suffix,
  digits = 1,
}: {
  value: number;
  suffix: string;
  digits?: number;
}) {
  const tone = value > 0 ? "positive" : value < 0 ? "negative" : "muted";
  return <span className={tone}>{signed(value, suffix, digits)}</span>;
}

function ComparisonMetric({
  label,
  baseline,
  scenario,
  delta,
  deltaSuffix,
  deltaDigits,
}: {
  label: string;
  baseline: string;
  scenario: string;
  delta: number;
  deltaSuffix: string;
  deltaDigits?: number;
}) {
  return (
    <article className="comparison-metric">
      <span>{label}</span>
      <div>
        <small>基準</small>
        <strong>{baseline}</strong>
      </div>
      <div>
        <small>変更後</small>
        <strong>{scenario}</strong>
      </div>
      <Delta
        value={delta}
        suffix={deltaSuffix}
        digits={deltaDigits}
      />
    </article>
  );
}

export function ComparisonView({
  data,
  histories,
  loading,
  onLoadData,
}: ComparisonViewProps) {
  const initialUniverse = useMemo(() => baselineUniverse(data), [data]);
  const [includedSymbols, setIncludedSymbols] =
    useState<Set<string>>(initialUniverse);
  const [search, setSearch] = useState("");
  const [newSymbol, setNewSymbol] = useState("");
  const [customTickers, setCustomTickers] = useState<CustomTicker[]>([]);
  const [scenario, setScenario] = useState<DashboardPayload | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const resultsRef = useRef<HTMLElement>(null);
  const revealResultsRef = useRef(false);

  useEffect(() => {
    setIncludedSymbols(initialUniverse);
    setScenario(null);
  }, [initialUniverse]);

  useEffect(() => {
    if (!scenario || !revealResultsRef.current || !resultsRef.current) return;
    revealResultsRef.current = false;
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    resultsRef.current.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
  }, [scenario]);

  const filteredTickers = useMemo(() => {
    const query = search.trim().toLowerCase();
    return TICKERS.filter((ticker) => ticker.symbol !== "QQQ").filter(
      (ticker) =>
        !query ||
        ticker.symbol.toLowerCase().includes(query) ||
        ticker.genre.toLowerCase().includes(query),
    );
  }, [search]);

  const removedSymbols = TICKERS.filter(
    (ticker) =>
      ticker.symbol !== "QQQ" &&
      initialUniverse.has(ticker.symbol) &&
      !includedSymbols.has(ticker.symbol),
  ).map((ticker) => ticker.symbol);

  const restoredSymbols = TICKERS.filter(
    (ticker) =>
      ticker.symbol !== "QQQ" &&
      !initialUniverse.has(ticker.symbol) &&
      includedSymbols.has(ticker.symbol),
  ).map((ticker) => ticker.symbol);

  const readyCustomTickers = customTickers.filter(
    (ticker) => ticker.status === "ready" && ticker.history,
  );
  const hasUnresolvedCustom = customTickers.some(
    (ticker) => ticker.status !== "ready",
  );

  const chartData = useMemo(() => {
    if (!scenario) return [];
    const baselineByMonth = new Map(
      data.backtest.rows.map((row) => [row.signalMonth, row]),
    );
    const scenarioByMonth = new Map(
      scenario.backtest.rows.map((row) => [row.signalMonth, row]),
    );
    const months = [
      ...new Set([
        ...baselineByMonth.keys(),
        ...scenarioByMonth.keys(),
      ]),
    ].sort();

    return months.map((month) => ({
      month: month.slice(0, 7),
      baseline: (baselineByMonth.get(month)?.equity ?? null) === null
        ? null
        : (baselineByMonth.get(month)?.equity ?? 1) * 100,
      scenario: (scenarioByMonth.get(month)?.equity ?? null) === null
        ? null
        : (scenarioByMonth.get(month)?.equity ?? 1) * 100,
    }));
  }, [data.backtest.rows, scenario]);

  const changedMonths = useMemo(() => {
    if (!scenario) return [];
    const baselineByMonth = new Map(
      data.backtest.rows.map((row) => [row.signalMonth, row]),
    );

    return scenario.backtest.rows
      .map((row) => {
        const baseline = baselineByMonth.get(row.signalMonth);
        const baselineReturn = baseline?.monthlyReturn ?? null;
        const scenarioReturn = row.monthlyReturn;
        const returnChanged =
          baselineReturn !== scenarioReturn &&
          !(
            baselineReturn !== null &&
            scenarioReturn !== null &&
            Math.abs(baselineReturn - scenarioReturn) < 0.000001
          );
        const picksChanged =
          (baseline?.picks.join(",") ?? "") !== row.picks.join(",");

        return {
          month: row.signalMonth,
          baselineReturn,
          scenarioReturn,
          delta:
            baselineReturn !== null && scenarioReturn !== null
              ? scenarioReturn - baselineReturn
              : null,
          baselinePicks: baseline?.picks ?? [],
          scenarioPicks: row.picks,
          changed: returnChanged || picksChanged,
        };
      })
      .filter((row) => row.changed)
      .slice(-12)
      .reverse();
  }, [data.backtest.rows, scenario]);

  function markDirty() {
    setScenario(null);
    setMessage(null);
  }

  function toggleTicker(symbol: string) {
    const next = new Set(includedSymbols);
    if (next.has(symbol)) {
      next.delete(symbol);
    } else {
      next.add(symbol);
    }
    setIncludedSymbols(next);
    runComparison(next, true);
  }

  async function loadCustomTicker(symbol: string) {
    setCustomTickers((current) =>
      current.map((ticker) =>
        ticker.symbol === symbol
          ? { symbol, status: "loading" }
          : ticker,
      ),
    );
    setScenario(null);

    try {
      const existingHistory = histories?.[symbol];
      const history =
        existingHistory ?? (await fetchYahooHistoryInBrowser(symbol));
      setCustomTickers((current) =>
        current.map((ticker) =>
          ticker.symbol === symbol
            ? { symbol, status: "ready", history }
            : ticker,
        ),
      );
      setMessage(`${symbol}を比較候補に追加しました。`);
    } catch (error) {
      setCustomTickers((current) =>
        current.map((ticker) =>
          ticker.symbol === symbol
            ? {
                symbol,
                status: "error",
                error:
                  error instanceof Error
                    ? error.message
                    : `${symbol}を取得できませんでした。`,
              }
            : ticker,
        ),
      );
    }
  }

  function addTicker() {
    const symbol = normalizeSymbol(newSymbol);
    setMessage(null);

    if (!symbol || !/^[A-Z0-9.^=-]{1,15}$/.test(symbol)) {
      setMessage("有効な銘柄コードを半角英数字で入力してください。");
      return;
    }
    if (symbol === "QQQ") {
      setMessage("QQQは市場判定に必須のため、常に比較対象へ含まれます。");
      setNewSymbol("");
      return;
    }

    const existing = TICKERS.find((ticker) => ticker.symbol === symbol);
    if (existing) {
      setIncludedSymbols((current) => new Set(current).add(symbol));
      setScenario(null);
      setMessage(`${symbol}を既存候補へ戻しました。`);
      setNewSymbol("");
      return;
    }

    if (customTickers.some((ticker) => ticker.symbol === symbol)) {
      setMessage(`${symbol}はすでに追加されています。`);
      return;
    }

    setCustomTickers((current) => [
      ...current,
      { symbol, status: "loading" },
    ]);
    setNewSymbol("");
    void loadCustomTicker(symbol);
  }

  function removeCustomTicker(symbol: string) {
    setCustomTickers((current) =>
      current.filter((ticker) => ticker.symbol !== symbol),
    );
    markDirty();
  }

  function runComparison(
    comparisonUniverse = includedSymbols,
    revealResults = false,
  ) {
    setMessage(null);
    if (!histories) {
      setMessage("比較には価格履歴の読み込みが必要です。");
      return;
    }
    if (hasUnresolvedCustom) {
      setMessage("追加銘柄の価格取得を完了してから比較してください。");
      return;
    }

    setRunning(true);
    try {
      const scenarioTickers: TickerConfig[] = [
        ...TICKERS.filter(
          (ticker) =>
            ticker.symbol === "QQQ" ||
            comparisonUniverse.has(ticker.symbol),
        ),
        ...readyCustomTickers.map((ticker) => ({
          symbol: ticker.symbol,
          genre: "Custom",
        })),
      ];
      const scenarioHistories = {
        ...histories,
        ...Object.fromEntries(
          readyCustomTickers.map((ticker) => [
            ticker.symbol,
            ticker.history as PricePoint[],
          ]),
        ),
      };
      const next = buildDashboard(
        scenarioHistories,
        scenarioTickers,
        {
          ...data.config,
          excludedTickers: [],
        },
      );
      revealResultsRef.current = revealResults;
      setScenario(next);
      setMessage("変更後のバックテストを計算しました。");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "比較バックテストを計算できませんでした。",
      );
    } finally {
      setRunning(false);
    }
  }

  const scenarioStats = scenario?.backtest.stats;
  const baselineStats = data.backtest.stats;
  const baselineInvestedMonths = data.backtest.rows.filter(
    (row) => row.market === "RiskOn" && row.picks.length > 0,
  ).length;
  const scenarioInvestedMonths = scenario?.backtest.rows.filter(
    (row) => row.market === "RiskOn" && row.picks.length > 0,
  ).length ?? 0;

  return (
    <div className="view-stack comparison-view">
      <div className="page-intro">
        <div>
          <h1>候補銘柄の比較検証</h1>
          <p>
            候補ユニバースだけを変更し、現在の戦略設定と同じ条件で結果を比較します。
          </p>
        </div>
        <div className="date-range">
          {data.config.backtestStart.replaceAll("-", ".")} - 最新
        </div>
      </div>

      <MaintenancePanel
        data={data}
        includedSymbols={includedSymbols}
        onToggle={toggleTicker}
      />

      <section className="comparison-builder">
        <div className="universe-panel">
          <div className="comparison-section-heading">
            <div>
              <h2>既存銘柄</h2>
              <p>
                {includedSymbols.size} / {TICKERS.length - 1}銘柄を候補に設定
              </p>
            </div>
            <div className="comparison-actions">
              <button
                className="text-button"
                onClick={() => {
                  setIncludedSymbols(
                    new Set(
                      TICKERS.filter((ticker) => ticker.symbol !== "QQQ").map(
                        (ticker) => ticker.symbol,
                      ),
                    ),
                  );
                  markDirty();
                }}
              >
                すべて入れる
              </button>
              <button
                className="text-button"
                onClick={() => {
                  setIncludedSymbols(new Set(initialUniverse));
                  markDirty();
                }}
              >
                基準に戻す
              </button>
            </div>
          </div>

          <label className="comparison-search">
            <span className="sr-only">既存銘柄を検索</span>
            <MagnifyingGlassIcon size={16} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="銘柄コードまたはテーマで検索"
            />
          </label>

          <div className="universe-list">
            {filteredTickers.map((ticker) => (
              <label
                className={
                  includedSymbols.has(ticker.symbol)
                    ? "universe-item selected"
                    : "universe-item"
                }
                key={ticker.symbol}
              >
                <input
                  type="checkbox"
                  checked={includedSymbols.has(ticker.symbol)}
                  onChange={() => toggleTicker(ticker.symbol)}
                />
                <span className="universe-check">
                  {includedSymbols.has(ticker.symbol) ? (
                    <CheckCircleIcon weight="fill" />
                  ) : null}
                </span>
                <strong>{ticker.symbol}</strong>
                <small>{ticker.genre}</small>
              </label>
            ))}
          </div>
        </div>

        <div className="custom-panel">
          <div className="comparison-section-heading">
            <div>
              <h2>新規銘柄</h2>
              <p>Yahoo Financeの調整後終値を取得します</p>
            </div>
          </div>

          <label className="new-symbol-field">
            <span>銘柄コード</span>
            <div>
              <input
                value={newSymbol}
                onChange={(event) =>
                  setNewSymbol(normalizeSymbol(event.target.value))
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    addTicker();
                  }
                }}
                placeholder="例: AAPL"
                maxLength={15}
              />
              <button
                type="button"
                className="primary-button"
                onClick={addTicker}
                disabled={!newSymbol}
              >
                <PlusIcon />
                追加
              </button>
            </div>
            <small>
              新規銘柄のテーマはCustomとして扱い、テーマ上限の対象外にします。
            </small>
          </label>

          <div className="custom-ticker-list">
            {customTickers.length ? (
              customTickers.map((ticker) => (
                <article
                  className={`custom-ticker ${ticker.status}`}
                  key={ticker.symbol}
                >
                  <div>
                    <strong>{ticker.symbol}</strong>
                    <span>
                      {ticker.status === "loading"
                        ? "価格履歴を取得中"
                        : ticker.status === "ready"
                          ? `${ticker.history?.length ?? 0}営業日を取得`
                          : ticker.error}
                    </span>
                  </div>
                  {ticker.status === "error" ? (
                    <button
                      type="button"
                      className="icon-text-button"
                      onClick={() => void loadCustomTicker(ticker.symbol)}
                    >
                      <ArrowCounterClockwiseIcon />
                      再試行
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="icon-button"
                    aria-label={`${ticker.symbol}を削除`}
                    onClick={() => removeCustomTicker(ticker.symbol)}
                  >
                    <TrashIcon />
                  </button>
                </article>
              ))
            ) : (
              <div className="comparison-empty">
                <ScalesIcon />
                <p>追加した銘柄がここに表示されます。</p>
              </div>
            )}
          </div>

          <div className="change-summary">
            <div>
              <span>外した既存銘柄</span>
              <strong>{removedSymbols.length}</strong>
              <small>{removedSymbols.join(", ") || "なし"}</small>
            </div>
            <div>
              <span>戻した既存銘柄</span>
              <strong>{restoredSymbols.length}</strong>
              <small>{restoredSymbols.join(", ") || "なし"}</small>
            </div>
            <div>
              <span>追加した新規銘柄</span>
              <strong>{customTickers.length}</strong>
              <small>
                {customTickers.map((ticker) => ticker.symbol).join(", ") ||
                  "なし"}
              </small>
            </div>
          </div>

          {!histories ? (
            <button
              type="button"
              className="secondary-button full-width"
              onClick={onLoadData}
              disabled={loading}
            >
              {loading ? "価格データを読込中" : "価格データを読み込む"}
            </button>
          ) : null}

          <button
            type="button"
            className="primary-button full-width compare-run-button"
            onClick={() => runComparison()}
            disabled={running || loading || hasUnresolvedCustom || !histories}
          >
            <ScalesIcon />
            {running ? "計算中" : "変更後と比較"}
          </button>

          {message ? (
            <p
              className={
                message.includes("計算しました") ||
                message.includes("追加しました") ||
                message.includes("戻しました")
                  ? "comparison-message success"
                  : "comparison-message"
              }
              role="status"
            >
              {message.includes("計算しました") ? (
                <CheckCircleIcon />
              ) : (
                <WarningCircleIcon />
              )}
              {message}
            </p>
          ) : null}
        </div>
      </section>

      {scenario && scenarioStats ? (
        <>
          <section ref={resultsRef}>
            <div className="section-heading">
              <div>
                <h2>結果の差</h2>
                <p>基準ユニバースと変更後を同じ期間で比較</p>
              </div>
            </div>
            <div className="comparison-metrics">
              <ComparisonMetric
                label="最終資産"
                baseline={`${number.format(baselineStats.finalEquity)}x`}
                scenario={`${number.format(scenarioStats.finalEquity)}x`}
                delta={scenarioStats.finalEquity - baselineStats.finalEquity}
                deltaSuffix="x"
                deltaDigits={2}
              />
              <ComparisonMetric
                label="CAGR"
                baseline={percent(baselineStats.cagr)}
                scenario={percent(scenarioStats.cagr)}
                delta={(scenarioStats.cagr - baselineStats.cagr) * 100}
                deltaSuffix="pt"
              />
              <ComparisonMetric
                label="最大DD"
                baseline={percent(baselineStats.maxDrawdown)}
                scenario={percent(scenarioStats.maxDrawdown)}
                delta={
                  (scenarioStats.maxDrawdown - baselineStats.maxDrawdown) *
                  100
                }
                deltaSuffix="pt"
              />
              <ComparisonMetric
                label="年率Vol"
                baseline={percent(baselineStats.annualizedVolatility)}
                scenario={percent(scenarioStats.annualizedVolatility)}
                delta={
                  (scenarioStats.annualizedVolatility -
                    baselineStats.annualizedVolatility) *
                  100
                }
                deltaSuffix="pt"
              />
              <ComparisonMetric
                label="投資月数"
                baseline={`${baselineInvestedMonths}か月`}
                scenario={`${scenarioInvestedMonths}か月`}
                delta={scenarioInvestedMonths - baselineInvestedMonths}
                deltaSuffix="か月"
                deltaDigits={0}
              />
            </div>
          </section>

          <section className="large-chart-panel">
            <div className="section-heading compact">
              <div>
                <h2>資産曲線の比較</h2>
                <p>初期資産を100として指数化</p>
              </div>
            </div>
            <div className="large-chart comparison-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid
                    vertical={false}
                    stroke="var(--line)"
                    strokeDasharray="2 4"
                  />
                  <XAxis
                    dataKey="month"
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
                  <Tooltip
                    formatter={(value, name) => [
                      `${number.format(Number(value))}`,
                      name === "baseline" ? "基準" : "変更後",
                    ]}
                    labelFormatter={(label) => String(label)}
                  />
                  <Legend
                    formatter={(value) =>
                      value === "baseline" ? "基準" : "変更後"
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="baseline"
                    stroke="var(--text-muted)"
                    strokeWidth={1.8}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="scenario"
                    stroke="var(--accent)"
                    strokeWidth={2.6}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section>
            <div className="section-heading">
              <div>
                <h2>変化した月</h2>
                <p>採用銘柄または月次リターンが変わった直近12件</p>
              </div>
            </div>
            {changedMonths.length ? (
              <div className="table-shell comparison-table">
                <table>
                  <thead>
                    <tr>
                      <th>シグナル月</th>
                      <th>基準リターン</th>
                      <th>変更後</th>
                      <th>差</th>
                      <th>変更後の採用銘柄</th>
                    </tr>
                  </thead>
                  <tbody>
                    {changedMonths.map((row) => (
                      <tr key={row.month}>
                        <td className="numeric">
                          {row.month.replaceAll("-", ".")}
                        </td>
                        <td className="numeric">
                          {percent(row.baselineReturn)}
                        </td>
                        <td className="numeric">
                          {percent(row.scenarioReturn)}
                        </td>
                        <td
                          className={`numeric ${
                            (row.delta ?? 0) >= 0 ? "positive" : "negative"
                          }`}
                        >
                          {row.delta === null
                            ? "N/A"
                            : signed(row.delta * 100, "pt")}
                        </td>
                        <td>
                          {row.scenarioPicks.length ? (
                            <div className="ticker-list">
                              {row.scenarioPicks.map((symbol) => (
                                <span key={symbol}>{symbol}</span>
                              ))}
                            </div>
                          ) : (
                            <span className="muted">配分なし</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="comparison-empty result-empty">
                <CheckCircleIcon />
                <p>この変更では月次結果に差がありませんでした。</p>
              </div>
            )}
          </section>
        </>
      ) : (
        <section className="comparison-placeholder">
          <ScalesIcon />
          <div>
            <h2>変更内容を設定して比較を実行</h2>
            <p>
              最終資産、CAGR、最大ドローダウン、資産曲線、変化した月を確認できます。
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
