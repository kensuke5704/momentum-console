"use client";

import {
  ArrowDownIcon,
  ArrowUpIcon,
  MagnifyingGlassIcon,
} from "@phosphor-icons/react";
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

type SortKey =
  | "symbol"
  | "track"
  | "priority"
  | "status"
  | "date"
  | "observations";
type SortState = {
  key: SortKey;
  direction: "desc" | "asc";
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

function sortValue(entry: WatchlistEntry, key: SortKey) {
  if (key === "symbol") return entry.symbol;
  if (key === "track") return trackLabel(entry.track);
  if (key === "priority") {
    const priorityRank: Record<string, number> = { A: 3, B: 2, C: 1 };
    return entry.priority ? (priorityRank[entry.priority] ?? 0) : null;
  }
  if (key === "status") return statusLabel(entry.status);
  if (key === "date") return entry.discoveryDate ?? entry.reviewDate ?? "";
  return entry.forwardEvidence?.completedObservations ?? 0;
}

function SortableHeader({
  label,
  sortKey,
  sort,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  sort: SortState | null;
  onSort: (key: SortKey) => void;
}) {
  const active = sort?.key === sortKey;
  return (
    <th
      aria-sort={
        active
          ? sort.direction === "desc"
            ? "descending"
            : "ascending"
          : "none"
      }
    >
      <button
        type="button"
        className={`watchlist-sort-button${active ? " active" : ""}`}
        onClick={() => onSort(sortKey)}
      >
        <span>{label}</span>
        {active ? (
          sort.direction === "desc" ? (
            <ArrowDownIcon aria-hidden="true" />
          ) : (
            <ArrowUpIcon aria-hidden="true" />
          )
        ) : null}
      </button>
    </th>
  );
}

export function WatchlistView({ refreshVersion }: { refreshVersion: number }) {
  const [search, setSearch] = useState("");
  const [track, setTrack] = useState<"all" | WatchlistTrack>("all");
  const [sort, setSort] = useState<SortState | null>(null);
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
    const filtered = entries.filter((entry) => {
      if (track !== "all" && entry.track !== track) return false;
      return (
        !query ||
        entry.symbol.toLowerCase().includes(query) ||
        entry.genre.toLowerCase().includes(query)
      );
    });
    if (!sort) return filtered;

    const direction = sort.direction === "desc" ? -1 : 1;
    return [...filtered].sort((left, right) => {
      const leftValue = sortValue(left, sort.key);
      const rightValue = sortValue(right, sort.key);
      if (leftValue === null && rightValue === null) return 0;
      if (leftValue === null) return 1;
      if (rightValue === null) return -1;
      const comparison =
        typeof leftValue === "number" && typeof rightValue === "number"
          ? leftValue - rightValue
          : String(leftValue).localeCompare(String(rightValue), "ja");
      return comparison * direction;
    });
  }, [entries, search, sort, track]);

  function handleSort(key: SortKey) {
    setSort((current) =>
      current?.key === key
        ? {
            key,
            direction: current.direction === "desc" ? "asc" : "desc",
          }
        : { key, direction: "desc" },
    );
  }

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
              <SortableHeader
                label="Ticker / Genre"
                sortKey="symbol"
                sort={sort}
                onSort={handleSort}
              />
              <SortableHeader
                label="区分"
                sortKey="track"
                sort={sort}
                onSort={handleSort}
              />
              <SortableHeader
                label="優先度"
                sortKey="priority"
                sort={sort}
                onSort={handleSort}
              />
              <SortableHeader
                label="状態"
                sortKey="status"
                sort={sort}
                onSort={handleSort}
              />
              <SortableHeader
                label="登録 / 監査日"
                sortKey="date"
                sort={sort}
                onSort={handleSort}
              />
              <SortableHeader
                label="Forward観測"
                sortKey="observations"
                sort={sort}
                onSort={handleSort}
              />
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
