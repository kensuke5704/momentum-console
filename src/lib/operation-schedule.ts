import {
  FROZEN_STRATEGY_FROZEN_AT,
  FROZEN_STRATEGY_ID,
} from "./frozen-strategy";

export type OperationScheduleItem = {
  id: string;
  cadence: string;
  title: string;
  timing: string;
  summary: string;
  tasks: string[];
  decisionRule: string;
};

export const OPERATION_PHASE = {
  status: "validation",
  label: "検証フェーズ",
  summary: "Frozen Strategyを固定してOOSを蓄積中",
  strategyId: FROZEN_STRATEGY_ID,
  frozenSince: FROZEN_STRATEGY_FROZEN_AT.slice(0, 7),
  formalReviewWindow: "2027.08–09",
} as const;

export const OPERATION_SCHEDULE = [
  {
    id: "monthly",
    cadence: "毎月",
    title: "OOS・Watchlist更新",
    timing: "米国市場の月末データ確定後",
    summary: "Frozen Strategyの実績とForward Evidenceを記録",
    tasks: [
      "Frozen StrategyのOOSを更新",
      "月次リターンと累積OOSリターンを記録",
      "QQQとの差、MaxDD、Volを更新",
      "当月の選定9銘柄とGenre構成を確認",
      "WatchlistのForward Evidenceを更新",
    ],
    decisionRule: "記録のみ。原則として戦略変更は行わない。",
  },
  {
    id: "quarterly",
    cadence: "適時",
    title: "新規Genre / Ticker探索",
    timing: "ユーザーによる候補調査時",
    summary: "調査済みの新規Genre / Ticker候補を確認",
    tasks: [
      "ユーザーが調査した新規Genre / Ticker候補を確認",
      "候補のGenre分類と投資対象としての適格性を確認",
      "新規Ticker候補をWatchlistへ登録",
      "Frozen Strategyでsanity check",
    ],
    decisionRule:
      "候補追加・Watch継続・Rejectは可能。過去CAGRが高いことだけを理由にUniverseへ採用しない。",
  },
  {
    id: "semiannual",
    cadence: "6か月",
    title: "中間監査",
    timing: "2月 / 8月",
    summary: "OOSの乖離と戦略の構造的異常を監査",
    tasks: [
      "OOS成績と過去バックテストの乖離を確認",
      "Genreへの収益集中を確認",
      "Watchlist候補のForward Evidenceを確認",
      "Legacy Review銘柄を確認",
      "IONQ / RCAT / FIX / MP等のreview状態を確認",
      "戦略の構造的異常がないか確認",
    ],
    decisionRule:
      "原則として戦略パラメータは変更しない。重大な構造問題がある場合のみ正式レビューを前倒しする。",
  },
  {
    id: "annual",
    cadence: "12か月",
    title: "正式レビュー",
    timing: "初回 2027.08–09",
    summary: "純OOSと各監査期間を比較して戦略を正式評価",
    tasks: [
      "Frozen Strategyの純OOS評価",
      "2020–2022 Legacy Auditとの比較",
      "2023–2026 Backtestとの比較",
      "TopN、Momentum Weight、QQQ MA、Surge Limitの妥当性を確認",
      "GenreMax / FrontierMaxの妥当性を確認",
      "WatchlistからUniverseへの採用判断",
      "Legacy Review銘柄の継続 / cleared / removed判断",
    ],
    decisionRule:
      "戦略パラメータやUniverseの正式変更を検討してよいタイミング。",
  },
  {
    id: "event-driven",
    cadence: "随時",
    title: "適格性イベント",
    timing: "イベント発生時",
    summary: "上場廃止・M&A等、投資対象としての適格性を確認",
    tasks: [
      "上場廃止",
      "M&A",
      "Ticker変更",
      "倒産 / 事業停止",
      "レバレッジETFの商品設計変更",
      "事業内容とGenre分類の乖離",
      "著しい流動性低下",
    ],
    decisionRule: "この場合は年次レビューを待たず対応可能。",
  },
] satisfies OperationScheduleItem[];
