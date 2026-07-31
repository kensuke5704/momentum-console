"use client";

import {
  ArrowClockwiseIcon,
  ArrowDownIcon,
  ArrowSquareOutIcon,
  ArrowUpIcon,
  BookmarkSimpleIcon,
  CheckIcon,
  MagnifyingGlassIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchYahooTrendingInBrowser,
  type YahooTrendingQuote,
} from "@/lib/yahoo-client";
import type { DashboardPayload } from "@/lib/types";

type Ranking = "attention" | "active" | "gainers";

const decimal = new Intl.NumberFormat("ja-JP", {
  maximumFractionDigits: 2,
});
const compact = new Intl.NumberFormat("ja-JP", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function percent(value: number) {
  return new Intl.NumberFormat("ja-JP", {
    style: "percent",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value / 100);
}

function buildAttentionList(
  active: YahooTrendingQuote[],
  gainers: YahooTrendingQuote[],
) {
  const rows = new Map<
    string,
    YahooTrendingQuote & { attentionRank: number }
  >();

  active.forEach((quote, index) => {
    rows.set(quote.symbol, {
      ...quote,
      attentionRank: active.length - index,
    });
  });
  gainers.forEach((quote, index) => {
    const current = rows.get(quote.symbol);
    const gainScore = gainers.length - index;
    rows.set(quote.symbol, {
      ...(current ?? quote),
      sources: current
        ? [...new Set([...current.sources, ...quote.sources])]
        : quote.sources,
      attentionRank: (current?.attentionRank ?? 0) + gainScore,
    });
  });

  return [...rows.values()]
    .sort((a, b) => b.attentionRank - a.attentionRank)
    .slice(0, 20);
}

function marketStatus(value: string) {
  if (value === "REGULAR") return "取引中";
  if (value === "PRE") return "プレ";
  if (value === "POST") return "時間外";
  return "終了";
}

export function ResearchView({ data }: { data: DashboardPayload }) {
  const [ranking, setRanking] = useState<Ranking>("attention");
  const [query, setQuery] = useState("");
  const [active, setActive] = useState<YahooTrendingQuote[]>([]);
  const [gainers, setGainers] = useState<YahooTrendingQuote[]>([]);
  const [asOf, setAsOf] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [watchlist, setWatchlist] = useState<string[]>([]);

  useEffect(() => {
    const saved = window.localStorage.getItem("momentum-research-watchlist");
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved) as unknown;
      if (Array.isArray(parsed)) {
        setWatchlist(
          parsed.filter((item): item is string => typeof item === "string"),
        );
      }
    } catch {
      window.localStorage.removeItem("momentum-research-watchlist");
    }
  }, []);

  const loadTrending = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchYahooTrendingInBrowser();
      setActive(result.active);
      setGainers(result.gainers);
      setAsOf(result.asOf);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "話題銘柄を取得できませんでした。",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTrending();
  }, [loadTrending]);

  const attention = useMemo(
    () => buildAttentionList(active, gainers),
    [active, gainers],
  );
  const sourceRows =
    ranking === "active" ? active : ranking === "gainers" ? gainers : attention;
  const rows = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return sourceRows;
    return sourceRows.filter(
      (row) =>
        row.symbol.toLowerCase().includes(normalized) ||
        row.name.toLowerCase().includes(normalized),
    );
  }, [query, sourceRows]);

  const momentumMap = useMemo(
    () => new Map(data.momentum.map((row) => [row.symbol, row])),
    [data.momentum],
  );

  function saveWatchlist(next: string[]) {
    setWatchlist(next);
    window.localStorage.setItem(
      "momentum-research-watchlist",
      JSON.stringify(next),
    );
  }

  function toggleWatchlist(symbol: string) {
    saveWatchlist(
      watchlist.includes(symbol)
        ? watchlist.filter((item) => item !== symbol)
        : [...watchlist, symbol],
    );
  }

  const formattedAsOf = asOf
    ? new Intl.DateTimeFormat("ja-JP", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(asOf))
    : "未取得";

  return (
    <div className="view-stack research-view">
      <div className="page-intro">
        <div>
          <h1>調査</h1>
          <p>米国市場の売買活況と急上昇から、話題銘柄を抽出します。</p>
        </div>
        <div className="research-live-meta">
          <span>{active[0] ? marketStatus(active[0].marketState) : "市場データ"}</span>
          <strong>{formattedAsOf}</strong>
          <button
            type="button"
            onClick={() => void loadTrending()}
            disabled={loading}
            aria-label="話題銘柄を更新"
          >
            <ArrowClockwiseIcon className={loading ? "spinning" : ""} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="warning-banner" role="status">
          <WarningCircleIcon size={20} weight="fill" />
          <span>{error}</span>
          <button type="button" onClick={() => void loadTrending()}>
            再取得
          </button>
        </div>
      ) : null}

      <section className="research-ranking-panel">
        <div className="research-ranking-head">
          <div className="research-ranking-tabs" role="tablist">
            <button
              className={ranking === "attention" ? "active" : ""}
              type="button"
              role="tab"
              aria-selected={ranking === "attention"}
              onClick={() => setRanking("attention")}
            >
              注目
              <small>総合</small>
            </button>
            <button
              className={ranking === "active" ? "active" : ""}
              type="button"
              role="tab"
              aria-selected={ranking === "active"}
              onClick={() => setRanking("active")}
            >
              出来高
              <small>Most Actives</small>
            </button>
            <button
              className={ranking === "gainers" ? "active" : ""}
              type="button"
              role="tab"
              aria-selected={ranking === "gainers"}
              onClick={() => setRanking("gainers")}
            >
              急上昇
              <small>Day Gainers</small>
            </button>
          </div>

          <label className="research-filter">
            <span className="sr-only">話題銘柄を絞り込む</span>
            <MagnifyingGlassIcon />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ticker または企業名"
            />
          </label>
        </div>

        <div className="research-ranking-note">
          {ranking === "attention"
            ? "出来高上位と上昇率上位の両方に現れる銘柄を優先"
            : ranking === "active"
              ? "当日の売買高が多い米国株"
              : "当日の上昇率が高い米国株"}
        </div>

        {loading && !rows.length ? (
          <div className="research-loading" aria-label="話題銘柄を取得中">
            {Array.from({ length: 8 }, (_, index) => (
              <span key={index} />
            ))}
          </div>
        ) : rows.length ? (
          <div className="research-table-wrap">
            <table className="research-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>銘柄</th>
                  <th>現在値</th>
                  <th>前日比</th>
                  <th>出来高</th>
                  <th>平常比</th>
                  <th>既存候補</th>
                  <th>調査</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => {
                  const momentum = momentumMap.get(row.symbol);
                  const saved = watchlist.includes(row.symbol);
                  const volumeRatio =
                    row.averageVolume > 0
                      ? row.volume / row.averageVolume
                      : null;
                  return (
                    <tr key={row.symbol}>
                      <td className="research-rank">
                        {String(index + 1).padStart(2, "0")}
                      </td>
                      <td>
                        <div className="ticker-cell">
                          <strong>{row.symbol}</strong>
                          <span>{row.name}</span>
                        </div>
                      </td>
                      <td className="numeric">
                        ${decimal.format(row.price)}
                      </td>
                      <td>
                        <span
                          className={`research-change ${row.changePercent >= 0 ? "up" : "down"}`}
                        >
                          {row.changePercent >= 0 ? (
                            <ArrowUpIcon />
                          ) : (
                            <ArrowDownIcon />
                          )}
                          {percent(row.changePercent)}
                        </span>
                      </td>
                      <td className="numeric">{compact.format(row.volume)}</td>
                      <td className="numeric">
                        {volumeRatio === null
                          ? "N/A"
                          : `${decimal.format(volumeRatio)}x`}
                      </td>
                      <td>
                        {momentum ? (
                          <span
                            className={`decision ${momentum.selected ? "selected" : momentum.eligible ? "eligible" : "excluded"}`}
                          >
                            {momentum.selected
                              ? "採用"
                              : momentum.eligible
                                ? "候補"
                                : "対象外"}
                          </span>
                        ) : (
                          <span className="muted">新規</span>
                        )}
                      </td>
                      <td>
                        <div className="research-row-actions">
                          <button
                            className={saved ? "saved" : ""}
                            type="button"
                            onClick={() => toggleWatchlist(row.symbol)}
                            aria-label={
                              saved
                                ? `${row.symbol}を調査リストから削除`
                                : `${row.symbol}を調査リストへ保存`
                            }
                          >
                            {saved ? (
                              <CheckIcon weight="bold" />
                            ) : (
                              <BookmarkSimpleIcon />
                            )}
                          </button>
                          <a
                            href={`https://finance.yahoo.com/quote/${encodeURIComponent(row.symbol)}/`}
                            target="_blank"
                            rel="noreferrer"
                            aria-label={`${row.symbol}をYahoo Financeで確認`}
                          >
                            詳細
                            <ArrowSquareOutIcon />
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="research-empty">
            <MagnifyingGlassIcon />
            <strong>該当する銘柄がありません</strong>
            <p>検索条件を変更してください。</p>
          </div>
        )}
      </section>

      <section className="research-watchlist">
        <div className="section-heading compact">
          <div>
            <h2>調査リスト</h2>
            <p>保存した銘柄をYahoo Financeで再確認</p>
          </div>
          <strong>{watchlist.length}</strong>
        </div>
        {watchlist.length ? (
          <div className="research-watch-grid">
            {watchlist.map((symbol) => {
              const quote =
                active.find((item) => item.symbol === symbol) ??
                gainers.find((item) => item.symbol === symbol);
              const momentum = momentumMap.get(symbol);
              return (
                <article key={symbol}>
                  <div className="ticker-cell">
                    <strong>{symbol}</strong>
                    <span>{quote?.name ?? momentum?.genre ?? "新規銘柄"}</span>
                  </div>
                  <div>
                    <span>前日比</span>
                    <strong
                      className={
                        quote && quote.changePercent < 0 ? "negative" : ""
                      }
                    >
                      {quote ? percent(quote.changePercent) : "N/A"}
                    </strong>
                  </div>
                  <a
                    href={`https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/`}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`${symbol}をYahoo Financeで確認`}
                  >
                    <ArrowSquareOutIcon />
                  </a>
                  <button
                    type="button"
                    onClick={() => toggleWatchlist(symbol)}
                    aria-label={`${symbol}を調査リストから削除`}
                  >
                    削除
                  </button>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="research-watch-empty">
            <BookmarkSimpleIcon />
            <p>ランキングの保存ボタンから銘柄を追加できます。</p>
          </div>
        )}
      </section>

      <p className="research-note">
        出典: Yahoo Finance Most Actives / Day Gainers。市場データは遅延する場合があります。
      </p>
    </div>
  );
}
