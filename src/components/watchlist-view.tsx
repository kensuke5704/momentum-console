"use client";

import { MagnifyingGlassIcon } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import bundledWatchlist from "../../data/universe-watchlist.json";

type WatchlistTrack = "candidate" | "legacy-review";

type WatchlistEntry = {
  symbol: string;
  genre: string;
  track: WatchlistTrack;
  priority: string | null;
  status: string;
  discoveryDate?: string;
  reviewDate?: string;
  forwardEvidence?: {
    completedObservations?: number;
  };
};

type WatchlistData = {
  updatedAt: string;
  entries: WatchlistEntry[];
};

const WATCHLIST_URL =
  "https://raw.githubusercontent.com/kensuke5704/momentum-console/main/data/universe-watchlist.json";
const initialWatchlist = bundledWatchlist as WatchlistData;

function isWatchlistData(value: unknown): value is WatchlistData {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<WatchlistData>;
  return (
    typeof candidate.updatedAt === "string" &&
    Array.isArray(candidate.entries) &&
    candidate.entries.every(
      (entry) =>
        typeof entry?.symbol === "string" &&
        typeof entry.genre === "string" &&
        (entry.track === "candidate" || entry.track === "legacy-review"),
    )
  );
}

function trackLabel(track: WatchlistTrack) {
  return track === "candidate" ? "新規候補" : "既存監査";
}

function statusLabel(status: string) {
  if (status === "watch") return "Watch";
  if (status === "review") return "Review";
  return status;
}

function compactDate(value?: string) {
  return value ? value.replaceAll("-", ".") : "—";
}

export function WatchlistView({ refreshVersion }: { refreshVersion: number }) {
  const [search, setSearch] = useState("");
  const [track, setTrack] = useState<"all" | WatchlistTrack>("all");
  const [watchlistData, setWatchlistData] =
    useState<WatchlistData>(initialWatchlist);

  useEffect(() => {
    const controller = new AbortController();

    async function loadLatestWatchlist() {
      try {
        const response = await fetch(`${WATCHLIST_URL}?ts=${Date.now()}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) return;
        const latest: unknown = await response.json();
        if (isWatchlistData(latest)) setWatchlistData(latest);
      } catch {
        // Keep the bundled list when GitHub is temporarily unavailable.
      }
    }

    void loadLatestWatchlist();
    return () => controller.abort();
  }, [refreshVersion]);

  const entries = watchlistData.entries;

  const candidateCount = entries.filter(
    (entry) => entry.track === "candidate",
  ).length;
  const reviewCount = entries.length - candidateCount;
  const visibleEntries = useMemo(() => {
    const query = search.trim().toLowerCase();
    return entries.filter((entry) => {
      if (track !== "all" && entry.track !== track) return false;
      return (
        !query ||
        entry.symbol.toLowerCase().includes(query) ||
        entry.genre.toLowerCase().includes(query)
      );
    });
  }, [entries, search, track]);

  return (
    <div className="view-stack watchlist-view">
      <section className="watchlist-summary" aria-label="ウォッチリスト概要">
        <div className="metric">
          <span>登録銘柄</span>
          <strong>{entries.length}</strong>
        </div>
        <div className="metric">
          <span>新規候補</span>
          <strong>{candidateCount}</strong>
        </div>
        <div className="metric">
          <span>既存監査</span>
          <strong>{reviewCount}</strong>
        </div>
        <div className="metric">
          <span>更新日</span>
          <strong className="watchlist-updated-at">
            {compactDate(watchlistData.updatedAt)}
          </strong>
        </div>
      </section>

      <div className="watchlist-toolbar">
        <label className="candidate-search watchlist-search">
          <MagnifyingGlassIcon aria-hidden="true" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Ticker またはGenreで検索"
            aria-label="ウォッチリストを検索"
          />
        </label>
        <label className="select-field watchlist-track-filter">
          <span>区分</span>
          <select
            value={track}
            onChange={(event) =>
              setTrack(event.target.value as "all" | WatchlistTrack)
            }
          >
            <option value="all">すべて</option>
            <option value="candidate">新規候補</option>
            <option value="legacy-review">既存監査</option>
          </select>
        </label>
      </div>

      <div className="table-shell watchlist-table">
        <table>
          <thead>
            <tr>
              <th>Ticker / Genre</th>
              <th>区分</th>
              <th>優先度</th>
              <th>状態</th>
              <th>登録 / 監査日</th>
              <th>Forward観測</th>
            </tr>
          </thead>
          <tbody>
            {visibleEntries.map((entry) => (
              <tr key={entry.symbol}>
                <td className="watchlist-ticker" data-label="Ticker / Genre">
                  <strong>{entry.symbol}</strong>
                  <span>{entry.genre}</span>
                </td>
                <td data-label="区分">
                  <span className={`watchlist-tag ${entry.track}`}>
                    {trackLabel(entry.track)}
                  </span>
                </td>
                <td className="numeric" data-label="優先度">
                  {entry.priority ?? "—"}
                </td>
                <td data-label="状態">{statusLabel(entry.status)}</td>
                <td className="numeric" data-label="登録 / 監査日">
                  {compactDate(entry.discoveryDate ?? entry.reviewDate)}
                </td>
                <td className="numeric" data-label="Forward観測">
                  {entry.forwardEvidence?.completedObservations ?? 0}回
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {visibleEntries.length === 0 ? (
          <p className="watchlist-empty">該当する銘柄はありません。</p>
        ) : null}
      </div>
    </div>
  );
}
