# Momentum Console — Stage21 Production

> **New chat / research continuation:** read [`MOMENTUM_HANDOFF.md`](MOMENTUM_HANDOFF.md) first. This is the stable entry point to the current canonical research handoff.

このNext.jsアプリは、SBI証券で実行可能なProduction portfolio **`momentum-stage21-sbi-2026-09-v1`** のsignal・target allocation・backtest・True Forward OOSを一元管理します。

> Documentation entry point: [`docs/README.md`](docs/README.md)  
> Current validation summary: [`docs/research/stage21-validation-summary-20260902.md`](docs/research/stage21-validation-summary-20260902.md)

旧Production `momentum-fixed60-2026-08-v1` は削除していません。現在はStage21の**内側のalpha/risk engine**としてTop2選定、stop/circuit/recovery、M3 shadow計算に利用します。旧Production仕様は [`docs/legacy/momentum-fixed60-2026-08-v1.md`](docs/legacy/momentum-fixed60-2026-08-v1.md) に保存しています。

## Production portfolio

| State | Fixed60 sleeve | GLDM | Cash |
|---|---:|---:|---:|
| NORMAL | 85.0% | 15.0% | 0.0% |
| YELLOW | 55.5% | 22.5% | 22.0% |
| DEEP | 25.5% | 30.0% | 44.5% |

借入・marginは使わず、gross exposureは100%以下です。SBIでは整数株で執行し、端数はCashとして残します。

Production portfolio parameterは [`src/lib/portfolio-config.ts`](src/lib/portfolio-config.ts)、Fixed60 inner parameterは [`src/lib/config.ts`](src/lib/config.ts) がsingle source of truthです。

詳細な凍結仕様は [`docs/production/stage21-sbi-2026-09-v1.md`](docs/production/stage21-sbi-2026-09-v1.md) を参照してください。

## Regime logic

### CFTC Yellow
- CFTC Traders in Financial Futures
- NASDAQ MINI contract 209742
- Asset Manager net = long - short
- 1週間のpublication lag
- 最新eligible net < 4 report前のnet ならYELLOW
- magnitude thresholdなし
- 公開遅延がある場合は実際のrelease dateを優先（2025 shutdown backlogをPIT補正済み）

### M3 Deep
M3は資金を投入しないshadow coreを使います。

```text
shadow core = 85% Fixed60 + 15% frozen Candidate G
```

- 20D shadow return < 0
- かつ20D QQQ比 underperformance <= -10pp
- 上記でDEEP
- gap > -3ppを5 sessions確認して解除

Candidate Gは**funded sleeveではありません**。

## Fixed60 inner engine

- SEC N-PORT breadth Universe Top80
- Point-in-Time: filingDate <= signal close date
- Momentum: 0×1M + 0.20×3M + 0.80×6M
- 1M +80%以上を除外
- stock score <= QQQ scoreを除外
- Top2、60/40
- QQQ 10-month MA gate
- individual stop -17.5%
- portfolio circuit -15%
- recovery: QQQ >100DMA、20D momentum >0、10 closes
- close confirmation -> next US open

## Rebalancing / execution

Stage21は以下で次の米国寄付きにfunded portfolioをrebuildします。

- 月次rebalance
- NORMAL/YELLOW/DEEPの変更
- Fixed60 funded targetの変更
- delayed N-PORT activationによるTop2変更

Outer portfolio transaction-cost modelは片道10bpのtraded notionalです。

## Dynamic Universe

SEC N-PORT quarterly ZIPは公式ファイルを手動取込します。

```bash
npm ci
npm run import:nport -- /absolute/path/YYYYqN_nport.zip
```

`sync:universe`は公開済みfilingだけからPIT Universe historyを再生成します。新しいquarterly ZIPが未取込の場合は直前のvalid Universeをfallbackとして維持し、遅延取込後に元のofficial month-end closeを使ってTop2を再評価します。

## Daily data pipeline

```bash
npm run sync:data
npm run sync:oos
```

`sync:data`は以下をatomicに更新します。

- Fixed60/Universe銘柄のYahoo adjusted OHLC
- GLDM
- CFTC Asset Manager positioning
- Fixed60 inner state
- Stage21 regime / target portfolio
- Stage21 historical backtest

必要な日足またはCFTCが揃わない場合はfail closedとし、古い/部分的なstateを公開しません。

## Console

UIの最上位Next ActionはFixed60単体ではなく**Stage21 funded portfolio**です。

表示対象:
- current NORMAL/YELLOW/DEEP
- CFTC eligible report / net / Yellow status
- M3 core/QQQ gap / Deep status
- 最終funded target（Top2 + GLDM + Cash）
- 次のUS Openでのrebalance指示
- inner Fixed60 Top2とrisk state
- Stage21 backtest
- Stage21 True Forward OOS

## Historical research reference

Release-aware same-sample Stage21 research through 2026-08-25:
- CAGR: 約48.61%
- MaxDD: 約-16.89%
- planning CAGR proxy: 約43.66%
- rolling36 median: 約43.66%
- rolling36 P10: 約35.19%
- rolling36 worst: 約23.42%

2026-09-02の再計算では暦年リターンは以下でした。

| Year | Return |
|---|---:|
| 2020 | +76.67% |
| 2021 | +55.10% |
| 2022 | -0.34% |
| 2023 | +86.94% |
| 2024 | +63.96% |
| 2025 | +45.15% |
| 2026 YTD through 2026-08-25 | +14.44% |

詳細・再現情報・PF・robustness結果は [`docs/research/stage21-validation-summary-20260902.md`](docs/research/stage21-validation-summary-20260902.md) に固定しています。

これはhistorical robustness referenceであり、将来CAGR 43.66%を保証・推定する統計的expected valueではありません。24–36か月windowではCAGR 40%を下回る期間も確認されています。

## SBI account-realism audit

next-open execution + 10bp + whole sharesで$10k / $25k / $50k / $100k / $250kを検証しました。全ケースでhistorical MaxDD 17%以内、$10kでもfractional simulationとのCAGR差は約-0.36ptでした。

## True Forward OOS

Stage21 OOSは **2026-09-02** 開始です。旧Fixed60 OOS（2026-08-31開始）はstrategy IDを分離し、新OOSへ継承しません。

OOSは毎日、以下を保存します。
- record date
- Fixed60 signal / Top2
- CFTC source report
- Stage21 regime
- funded targets
- intended execution date
- equity / drawdown

最初の約3か月はCAGRで判断せず、data timing・CFTC/M3 state・next-open execution parityを監査します。

事前固定gate:
- MaxDD -17%: AMBER review
- MaxDD -25%: RED kill
- 12M+: CAGR <0 かつ MaxDD <=-17%: RED
- 24M+: gross CAGR <15%: RED
- 36M+: gross CAGR <25%: RED

rule変更時は新strategy IDと新OOS clockを作成します。

## Validation

```bash
npm run check
```

tests / TypeScript / ESLint / Next.js buildを一括実行します。
