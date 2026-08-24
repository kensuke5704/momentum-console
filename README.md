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

初回または新しいSEC quarter:

```bash
npm run sync:sec
npm run sync:universe
```

日次価格・state・backtest・Forward OOS:

```bash
npm run sync:data
npm run sync:oos
```

`sync:sec`はSEC公式quarterly bulk ZIPをstream処理し、正規化済みfiling cacheを増分更新します。`sync:universe`はQQQのofficial trading close dateをsignal dateとしてPIT Universe historyを再生成します。`sync:data`はYahoo Financeのadjusted closeと同一adjustment factorをOpen/High/Lowへ適用し、splitによる偽stopを防ぎます。

GitHub Actionsは22:20 UTCに実行します。これはESTで17:20、EDTで18:20となり、DSTのどちらでも米国Close後です。画面の「最新データを読込」はActionsが公開した`market-data.json`をcache無効で再取得します。ブラウザ内に別のsignalロジックはありません。

月初のUniverse workflowはN-PORT historyを更新し、日次workflowはstop/circuit/recoveryとNext Actionを更新します。

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

Forward OOSは新Strategy IDから独立して開始し、旧戦略のequityへ接続しません。signal、Universe、ranking、target weights、market/risk state、execution、trigger historyを保存します。

Benchmarkは利用可能な期間のactual `TQQQ Buy & Hold`です。将来synthetic proxyを追加する場合は`Synthetic 3x QQQ proxy`と明示し、actual TQQQと混同しません。

## Watchlist

Watchlistは`Research / observation only`です。Watchlist membershipをProduction Universeへ強制追加する経路はありません。

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
