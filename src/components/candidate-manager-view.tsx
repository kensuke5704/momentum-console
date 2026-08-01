"use client";

import {
  CheckCircleIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ScalesIcon,
  TrashIcon,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import { MaintenancePanel } from "@/components/maintenance-panel";
import { TICKERS } from "@/lib/config";
import type { DashboardPayload } from "@/lib/types";

const STORAGE_KEY = "momentum-candidate-universe";

type SavedUniverse = {
  included: string[];
  custom: string[];
};

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

export function CandidateManagerView({ data }: { data: DashboardPayload }) {
  const initialUniverse = useMemo(() => baselineUniverse(data), [data]);
  const [includedSymbols, setIncludedSymbols] = useState(initialUniverse);
  const [customSymbols, setCustomSymbols] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [newSymbol, setNewSymbol] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved) as SavedUniverse;
      if (Array.isArray(parsed.included)) {
        const known = new Set(
          TICKERS.filter((ticker) => ticker.symbol !== "QQQ").map(
            (ticker) => ticker.symbol,
          ),
        );
        setIncludedSymbols(
          new Set(parsed.included.filter((symbol) => known.has(symbol))),
        );
      }
      if (Array.isArray(parsed.custom)) {
        setCustomSymbols(
          parsed.custom.filter(
            (symbol): symbol is string =>
              typeof symbol === "string" &&
              /^[A-Z0-9.^=-]{1,15}$/.test(symbol),
          ),
        );
      }
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  function save(nextIncluded: Set<string>, nextCustom: string[]) {
    setIncludedSymbols(nextIncluded);
    setCustomSymbols(nextCustom);
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        included: [...nextIncluded],
        custom: nextCustom,
      } satisfies SavedUniverse),
    );
  }

  function toggleTicker(symbol: string) {
    const next = new Set(includedSymbols);
    if (next.has(symbol)) {
      if (!window.confirm(`${symbol}を候補から外しますか？`)) return;
      next.delete(symbol);
    } else {
      next.add(symbol);
    }
    save(next, customSymbols);
    setMessage("");
  }

  function addTicker() {
    const symbol = normalizeSymbol(newSymbol);
    setMessage("");

    if (!symbol || !/^[A-Z0-9.^=-]{1,15}$/.test(symbol)) {
      setMessage("有効な銘柄コードを半角英数字で入力してください。");
      return;
    }
    if (symbol === "QQQ") {
      setMessage("QQQは市場判定に使用するため、候補管理の対象外です。");
      setNewSymbol("");
      return;
    }

    const existing = TICKERS.some((ticker) => ticker.symbol === symbol);
    if (existing) {
      const next = new Set(includedSymbols).add(symbol);
      save(next, customSymbols);
      setMessage(`${symbol}を既存候補へ戻しました。`);
      setNewSymbol("");
      return;
    }
    if (customSymbols.includes(symbol)) {
      setMessage(`${symbol}はすでに追加されています。`);
      return;
    }

    save(includedSymbols, [...customSymbols, symbol]);
    setMessage(`${symbol}を新規候補に追加しました。`);
    setNewSymbol("");
  }

  function removeCustomTicker(symbol: string) {
    if (!window.confirm(`${symbol}を追加銘柄から削除しますか？`)) return;
    save(
      includedSymbols,
      customSymbols.filter((item) => item !== symbol),
    );
    setMessage("");
  }

  const filteredTickers = TICKERS.filter((ticker) => {
    if (ticker.symbol === "QQQ") return false;
    const normalizedSearch = search.trim().toLowerCase();
    return (
      !normalizedSearch ||
      ticker.symbol.toLowerCase().includes(normalizedSearch) ||
      ticker.genre.toLowerCase().includes(normalizedSearch)
    );
  });
  const removedSymbols = TICKERS.filter(
    (ticker) =>
      ticker.symbol !== "QQQ" &&
      initialUniverse.has(ticker.symbol) &&
      !includedSymbols.has(ticker.symbol),
  ).map((ticker) => ticker.symbol);

  return (
    <div className="view-stack comparison-view">
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
                {includedSymbols.size.toLocaleString("ja-JP")} /{" "}
                {(TICKERS.length - 1).toLocaleString("ja-JP")}銘柄
              </p>
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
              <p>銘柄コードで候補を追加</p>
            </div>
          </div>

          <label className="custom-ticker-input">
            <span>銘柄コード</span>
            <div>
              <input
                value={newSymbol}
                onChange={(event) => setNewSymbol(event.target.value)}
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
          </label>

          {message ? <p className="comparison-message">{message}</p> : null}

          <div className="custom-ticker-list">
            {customSymbols.length ? (
              customSymbols.map((symbol) => (
                <article className="custom-ticker ready" key={symbol}>
                  <div>
                    <strong>{symbol}</strong>
                    <span>追加済み</span>
                  </div>
                  <button
                    type="button"
                    className="icon-button"
                    aria-label={`${symbol}を削除`}
                    onClick={() => removeCustomTicker(symbol)}
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
              <strong>{removedSymbols.length.toLocaleString("ja-JP")}</strong>
              <small>{removedSymbols.join(", ") || "なし"}</small>
            </div>
            <div>
              <span>追加した新規銘柄</span>
              <strong>{customSymbols.length.toLocaleString("ja-JP")}</strong>
              <small>{customSymbols.join(", ") || "なし"}</small>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
