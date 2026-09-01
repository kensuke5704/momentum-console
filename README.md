# Momentum Console — Dynamic Production Strategy

`momentum-dynamic-2026-08-v1` を唯一のProduction Strategyとして表示・検証するNext.jsアプリです。固定TickerリストやWatchlistを採用Universeへ混ぜず、各signal monthで公開済みだったSEC Form N-PORT holdingsからPoint-in-Time Universeを再構築します。

## Strategy

- Universe: SEC N-PORT breadth score Top 80
- Point-in-Time: `filingDate <= signal close date`、各`seriesId`の公開済み最新filingだけを使用
- Momentum: `0 × 1M + 0.20 × 3M + 0.80 × 6M`
- Exclusions: 1M returnが+80%以上、またはMomentum scoreがQQQ以下
- Selection: Top2。2銘柄未満なら新規Risk-On portfolioを組まない
- Allocation: 通常50/50、raw Momentumのcross-sectional `zGap >= 0.25`なら70/30。Top1上限70%
- Market gate: QQQ close > QQQ 10-month moving average
- Individual stop: entryから-17.5%をdaily Closeで確認し、翌session Openで全売却
- Portfolio circuit: equity peakから-15%をdaily Closeで確認し、翌session Openで全売却
- Persistent recovery: monthly gate RiskOn、QQQ > 100DMA、20 trading-day momentum > 0を10 closes連続確認し、翌session Openで再投入
- Execution: month-end signal、stop、circuit、recoveryのすべてが`confirmation close → next US session open`
- Cost: entry/exit双方へ片道10bp

Production parameterは[`src/lib/config.ts`](src/lib/config.ts)だけで定義します。UI、同期script、signal、backtest、OOSは同じ定義をimportし、別parameterを持ちません。

## Dynamic Universe

ETF sourceはleveraged/inverse、option income、buffer、fixed income、allocation/income、broad benchmark型を除外します。holdings数10〜120、positive weight合計50以上、Top10 weight合計25以上を満たすETFだけを使います。

各stockについて`etfCount`、`aggregateWeight`、`maxWeight`、`recencyWeight`を計算します。

```text
recencyFactor = exp(-ageDays / 120)

Universe score =
3.0 × log1p(etfCount)
+ 0.5 × log1p(aggregateWeight)
+ 0.5 × log1p(recencyWeight)
```

`etfCount >= 2 OR maxWeight >= 4`だけをscore順に並べ、Top80をfreezeします。株価returnはUniverse admissionに使用しません。出力にはsource filings、rank、各score component、added/removedを保存します。

## Data workflow

新しいSEC quarterは、SEC公式サイトから人が取得したquarterly ZIPだけを手動で取り込みます。アプリやGitHub ActionsからSECへ直接ダウンロードしません。

```bash
npm ci
npm run import:nport -- /absolute/path/YYYYqN_nport.zip
```

日次価格・state・backtest・Forward OOS:

```bash
npm run sync:data
npm run sync:oos
```

`import:nport`はZIP構造と必須headerを検証して正規化済みfiling cacheを更新し、Universe、atlas、market data、OOS、tests/typecheck/lint/buildまで一括実行します。詳細は[`docs/runbooks/manual-nport-update.md`](docs/runbooks/manual-nport-update.md)を参照してください。`sync:universe`はQQQのofficial trading close dateをsignal dateとしてPIT Universe historyを再生成します。`sync:data`はYahoo Financeのadjusted closeと同一adjustment factorをOpen/High/Lowへ適用し、splitによる偽stopを防ぎます。Yahooの日足`close`/`adjclose`がClose後も未生成の場合は、16:00 ET（短縮日は13:00 ET）のregular-market時刻、`regularMarketPrice`、30分足の始値・全session coverage・closing markerが一致した場合だけ、検証済み暫定日足を使用します。不一致時はQQQをstrategy clockとして当日stateをatomicに進めず、部分更新を残しません。暫定OOS点は正式なadjusted日足到着時に自動置換します。

GitHub ActionsはClose後の22:20 UTCに加え、00:30 UTC（Close後retry）と次回Open前の08:30 / 10:30 / 12:30 UTCにも再取得します。定期・手動のデータ更新では、必要な日足または検証済みfallbackが揃わなければworkflowを失敗させ、直前の正常な公開版を維持します。古い価格を混ぜたstateや部分更新は公開しません。画面の「最新データを読込」はActionsが公開した`market-data.json`をcache無効で再取得します。ブラウザ内に別のsignalロジックはありません。

月初のUniverse workflowは00:30 UTC（09:30 JST）に、最後に手動取込・検証されたN-PORT sourceからUniverse historyを再構築します。日次workflowは確定日足を検証できた時点でstop/circuit/recovery、OOS、Next Actionを更新します。

## State machine

```text
CASH / INVESTED
  ├─ monthly RiskOff close ──────> LOCKED_MARKET ─┐
  ├─ individual stop close ──────> LOCKED_STOP ───┤
  └─ portfolio circuit close ────> LOCKED_CIRCUIT ┤
                                                  ↓ next OPEN exit
                                         WAITING_RECOVERY
                                                  ↓ 10th confirming CLOSE
                                          READY_NEXT_OPEN
                                                  ↓ next OPEN entry
                                              INVESTED
```

Production signalとhistorical backtestは[`src/lib/strategy/state-machine.ts`](src/lib/strategy/state-machine.ts)の同じtransitionを使用します。Closeで成立した条件をsame Close/Openへ遡って約定させません。overnight gapは実際の翌Open価格で損益に反映します。

## Forward OOS and benchmark

Backtest表示は`2026-08-25`に凍結した[`public/data/backtest-frozen.json`](public/data/backtest-frozen.json)だけを参照し、日次価格同期では変更しません。

Forward OOSは`2026-08-25`から新Strategy IDで独立して開始し、旧戦略や凍結Backtestのequityへ接続しません。平日の米国市場Close後にGitHub ActionsがYahoo Financeの実OHLCを取得し、Productionと同じstate machine・next-open約定・取引コストで日次OOS equityを更新します。確定済みのOOS日次点は上書きせず、新しい取引日だけを追加します。検証済みregular-close fallbackを使った日だけは暫定として記録し、Yahooの正式なadjusted日足到着時に置換します。signal、Universe、ranking、target weights、market/risk state、execution、trigger historyも保存します。

Benchmarkは利用可能な期間のactual `TQQQ Buy & Hold`です。将来synthetic proxyを追加する場合は`Synthetic 3x QQQ proxy`と明示し、actual TQQQと混同しません。

## Validation

```bash
npm run test
npm run typecheck
npm run lint
npm run build
npm run check
```

testsはfuture-filing leakage、Universe cap/score、0/20/80、surge、QQQ comparison、Top2、adaptive weights、70% cap、next-open、overnight gap、stop、circuit、persistent recovery、transaction cost、legacy fixed TICKERS非依存を検証します。

## Known limitations

- 単一銘柄のovernight gap自体は防げません。翌Openで実現損益へ反映します。
- SEC/Yahooの公開データ品質・訂正・欠損に依存します。
- Dashboardは注文計画を表示しますがbrokerへ自動発注しません。実約定との差は運用時に記録が必要です。
- 研究結果は将来のperformanceを保証しません。
