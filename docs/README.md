# Momentum Console — Documentation Index

このディレクトリは、現在のProduction戦略、研究結果、旧仕様、運用手順を混同しないための入口です。

## 1. Current Production

**Production strategy:** `momentum-stage21-sbi-2026-09-v1`

まず読むもの:
- [`production/stage21-sbi-2026-09-v1.md`](production/stage21-sbi-2026-09-v1.md) — 現行戦略の凍結仕様
- [`production/stage21-ui-source-of-truth.md`](production/stage21-ui-source-of-truth.md) — consoleで何を運用上の正とするか
- [`production/stage21-console-action-display.md`](production/stage21-console-action-display.md) — Next Action表示仕様
- [`production/stage21-console-action-display-verified.md`](production/stage21-console-action-display-verified.md) — PC/スマホ表示確認

Productionの資金配分:

| State | Fixed60 inner sleeve | GLDM | Cash |
|---|---:|---:|---:|
| NORMAL | 85.0% | 15.0% | 0.0% |
| YELLOW | 55.5% | 22.5% | 22.0% |
| DEEP | 25.5% | 30.0% | 44.5% |

Fixed60は現在もTop2選定・stop/circuit/recovery・M3 shadow-coreに使用しますが、Production/OOS identityそのものではありません。

## 2. Current Evidence Snapshot

Stage21 rounded v1 の release-aware same-sample historical reference through 2026-08-25:

- Historical CAGR: **48.61%**
- Historical MaxDD: **-16.89%**
- Planning proxy: **43.66%**
- Rolling 36M median CAGR: **43.66%**
- Rolling 36M P10 CAGR: **35.19%**
- Rolling 36M worst CAGR: **23.42%**

これらは将来期待値ではなく、historical robustness diagnosticsです。

True Forward OOS:
- strategy ID: `momentum-stage21-sbi-2026-09-v1`
- start: **2026-09-02**
- legacy Fixed60 OOSとは分離
- ルール変更時は新strategy ID・新OOS clockとする

OOS gateは `src/lib/oos-action-gate.ts` に事前固定されています。

## 3. Research

[`research/`](research/) は検証・監査用です。Production仕様と混同しないでください。

主要な研究テーマ:
- Fixed60 robustness / leave-one-out / delay / cost stress
- independent Candidate G / U
- M3 defensive architecture
- DBMF / BTAL / credit / VIX / STLFSI / CFTC / put-call experiments
- SBIで購入可能な代替資産の検証
- Stage21 plateau / cost / delay / ablation / PIT / rolling-window / account-realism audits
- overfitting / selection-bias audit

研究上の重要なガバナンス:
- Stage21 PASS後に同一sampleでweight/thresholdを再最適化しない
- CFTC 4-week lookback、participant class、Yellow/Deep weights、M3 threshold等を同一sampleで再探索しない
- Planning proxyをTrue Forward expected CAGRと呼ばない
- CPCMをmomentum戦略の主要期待収益推定に使わない

## 4. Legacy

[`legacy/`](legacy/) は旧Production仕様・旧OOS・過去設計の参照用です。

旧Fixed60は削除せず保存しますが、新Stage21 OOSへ混入させません。

## 5. Runbooks

[`runbooks/`](runbooks/) は日常運用・データ更新・障害時対応の手順です。

日々の投資判断はconsole上部の **Next Action** を運用上のsource of truthとします。

## 6. Code/Data Map

- `src/lib/` — Production strategy / portfolio / OOS logic
- `scripts/sync-data.ts` — 市場価格・CFTC取得、Stage21 state生成
- `scripts/sync-oos.ts` — True Forward OOS更新
- `scripts/build-universe.ts` — PIT Dynamic Universe再構築
- `data/` — audit可能な入力・Universe履歴
- `public/data/` — console表示用生成データ
- `.github/workflows/pages.yml` — 日次データ更新・Pages deploy
- `.github/workflows/monthly-universe.yml` — 月次Universe再構築

## 7. Naming Rule Going Forward

新しい成果は次の場所に保存してください。

- 現行Production仕様・運用上必須の文書 → `docs/production/`
- historical test / audit / robustness結果 → `docs/research/`
- 廃止済み仕様 → `docs/legacy/`
- 手順書 → `docs/runbooks/`

研究結果をProductionへ反映するときは、必ずstrategy IDとOOS clockの扱いを明示します。
