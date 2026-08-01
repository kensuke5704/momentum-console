import type { DashboardPayload } from "@/lib/types";

export function MaintenancePanel({
  data,
  includedSymbols,
  onToggle,
}: {
  data: DashboardPayload;
  includedSymbols: ReadonlySet<string>;
  onToggle: (symbol: string) => void;
}) {
  const recentRows = data.backtest.rows.slice(-24);
  const candidates = data.momentum
    .filter((row) => !row.selected)
    .map((row) => {
      const pickedRows = recentRows.filter((period) =>
        period.picks.includes(row.symbol),
      );
      const lastPicked = pickedRows.at(-1)?.signalMonth ?? null;
      const pickCount = pickedRows.length;
      let judge = "維持候補";
      let priority = 4;

      if (!row.eligible && pickCount <= 1) {
        judge = "強い削除候補";
        priority = 1;
      } else if (pickCount <= 2) {
        judge = "削除候補";
        priority = 2;
      } else if (!row.eligible) {
        judge = "非Eligible";
        priority = 3;
      } else if ((row.rank ?? 999) > data.config.topN * 2) {
        judge = "低順位";
        priority = 3;
      }

      return { ...row, pickCount, lastPicked, judge, priority };
    })
    .sort(
      (a, b) =>
        a.priority - b.priority ||
        a.pickCount - b.pickCount ||
        (b.rank ?? 999) - (a.rank ?? 999),
    )
    .slice(0, 8);

  return (
    <section className="maintenance-panel">
      <div className="section-heading compact">
        <div>
          <h2>整理候補</h2>
          <p>直近24か月の採用履歴と現在の適格判定から抽出</p>
        </div>
      </div>
      <div className="maintenance-grid">
        {candidates.map((row) => {
          const isIncluded = includedSymbols.has(row.symbol);
          return (
          <article
            className={isIncluded ? "is-included" : "is-excluded"}
            key={row.symbol}
          >
            <button
              type="button"
              className="maintenance-card-button"
              aria-label={`${row.symbol}を候補から${isIncluded ? "外す" : "戻す"}`}
              aria-pressed={!isIncluded}
              onClick={() => onToggle(row.symbol)}
            />
            <div>
              <strong>{row.symbol}</strong>
              <span>{row.genre}</span>
            </div>
            <dl>
              <div>
                <dt>採用回数</dt>
                <dd>{row.pickCount.toLocaleString("ja-JP")}</dd>
              </div>
              <div>
                <dt>最終採用</dt>
                <dd>{row.lastPicked ? row.lastPicked.slice(0, 7) : "なし"}</dd>
              </div>
            </dl>
            <span className={`review-tag priority-${row.priority}`}>
              {row.judge}
            </span>
            <small className="maintenance-card-hint">
              クリックで候補から{isIncluded ? "除外" : "復帰"}
            </small>
          </article>
          );
        })}
      </div>
    </section>
  );
}
