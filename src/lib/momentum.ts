import type {
  BacktestRow,
  BacktestStats,
  DashboardPayload,
  MarketState,
  MomentumRow,
  PortfolioRow,
  PricePoint,
  StrategyConfig,
  TickerConfig,
} from "./types";

type MonthPoint = {
  key: string;
  date: string;
  close: number;
};

type Candidate = {
  symbol: string;
  genre: string;
  current: number;
  oneMonth: number;
  threeMonth: number;
  sixMonth: number;
  score: number;
  entryDate: string | null;
  exitDate: string | null;
  nextReturn: number | null;
  provisional: boolean;
};

function toMonthKey(date: string) {
  return date.slice(0, 7);
}

function toMonthEnd(monthKey: string) {
  const [year, month] = monthKey.split("-").map(Number);
  return new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10);
}

function addDays(date: string, days: number) {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

function monthlyHistory(points: PricePoint[]): MonthPoint[] {
  const lastByMonth = new Map<string, PricePoint>();
  for (const point of points) {
    lastByMonth.set(toMonthKey(point.date), point);
  }
  return [...lastByMonth.entries()]
    .map(([key, point]) => ({ key, ...point }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

function priceOnOrAfter(points: PricePoint[], date: string) {
  return points.find((point) => point.date >= date) ?? null;
}

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function stdev(values: number[]) {
  if (values.length <= 1) return 0;
  const average = mean(values);
  const variance =
    values.reduce((sum, value) => sum + (value - average) ** 2, 0) /
    (values.length - 1);
  return Math.sqrt(variance);
}

function selectWithLimits(
  candidates: Candidate[],
  config: StrategyConfig,
) {
  const selected: Candidate[] = [];
  const genreCounts = new Map<string, number>();
  let frontierCount = 0;
  const frontierGenres = new Set(config.frontierGenres);

  for (const candidate of candidates) {
    const genreLimit = config.genreLimits[candidate.genre];
    const currentGenreCount = genreCounts.get(candidate.genre) ?? 0;

    if (genreLimit !== undefined && currentGenreCount >= genreLimit) {
      continue;
    }

    const isFrontier = frontierGenres.has(candidate.genre);
    if (isFrontier && frontierCount >= config.frontierMax) {
      continue;
    }

    selected.push(candidate);
    genreCounts.set(candidate.genre, currentGenreCount + 1);
    if (isFrontier) frontierCount += 1;

    if (selected.length >= config.topN) break;
  }

  return selected;
}

function buildAtIndex({
  index,
  qqqMonths,
  monthMaps,
  histories,
  tickers,
  config,
  requireTradePrices,
}: {
  index: number;
  qqqMonths: MonthPoint[];
  monthMaps: Record<string, Map<string, number>>;
  histories: Record<string, PricePoint[]>;
  tickers: TickerConfig[];
  config: StrategyConfig;
  requireTradePrices: boolean;
}) {
  if (index < Math.max(9, 6) || index >= qqqMonths.length) return null;

  const currentKey = qqqMonths[index].key;
  const qqqWindow = qqqMonths
    .slice(index - config.qqqMaMonths + 1, index + 1)
    .map((point) => point.close);

  if (qqqWindow.length < config.qqqMaMonths) return null;

  const qqq = qqqMonths[index].close;
  const ma10 = mean(qqqWindow);
  const state: MarketState = qqq > ma10 ? "RiskOn" : "Cash";

  const qqq1 = qqqMonths[index - 1]?.close;
  const qqq3 = qqqMonths[index - 3]?.close;
  const qqq6 = qqqMonths[index - 6]?.close;
  if (!qqq1 || !qqq3 || !qqq6) return null;

  const qqqScore =
    config.weights.oneMonth * (qqq / qqq1 - 1) +
    config.weights.threeMonth * (qqq / qqq3 - 1) +
    config.weights.sixMonth * (qqq / qqq6 - 1);

  if (state === "Cash") {
    return {
      state,
      qqq,
      ma10,
      qqqScore,
      candidates: [] as Candidate[],
      selected: [] as Candidate[],
    };
  }

  const signalDate = toMonthEnd(currentKey);
  const nextMonthKey = qqqMonths[index + 1]?.key;
  const exitSignalDate = nextMonthKey ? toMonthEnd(nextMonthKey) : null;
  const excluded = new Set(
    config.excludedTickers.map((symbol) => symbol.toUpperCase()),
  );
  const candidates: Candidate[] = [];

  for (const ticker of tickers) {
    const { symbol, genre } = ticker;
    if (symbol === "QQQ" || excluded.has(symbol)) continue;

    const map = monthMaps[symbol];
    if (!map) continue;

    const current = map.get(currentKey);
    const oneMonth = map.get(qqqMonths[index - 1].key);
    const threeMonth = map.get(qqqMonths[index - 3].key);
    const sixMonth = map.get(qqqMonths[index - 6].key);

    if (!current || !oneMonth || !threeMonth || !sixMonth) continue;

    const m1 = current / oneMonth - 1;
    const m3 = current / threeMonth - 1;
    const m6 = current / sixMonth - 1;
    const score =
      config.weights.oneMonth * m1 +
      config.weights.threeMonth * m3 +
      config.weights.sixMonth * m6;

    if (m1 >= config.surgeLimit || score <= qqqScore) continue;

    let entryDate: string | null = null;
    let exitDate: string | null = null;
    let nextReturn: number | null = null;
    let provisional = false;

    if (requireTradePrices) {
      const entry = priceOnOrAfter(histories[symbol], addDays(signalDate, 3));
      const exit = exitSignalDate
        ? priceOnOrAfter(histories[symbol], addDays(exitSignalDate, 3))
        : null;

      if (!entry) continue;
      entryDate = entry.date;

      if (!exit) {
        provisional = true;
      } else {
        exitDate = exit.date;
        nextReturn = exit.close / entry.close - 1;
      }
    }

    candidates.push({
      symbol,
      genre,
      current,
      oneMonth: m1,
      threeMonth: m3,
      sixMonth: m6,
      score,
      entryDate,
      exitDate,
      nextReturn,
      provisional,
    });
  }

  candidates.sort((a, b) => b.score - a.score);

  return {
    state,
    qqq,
    ma10,
    qqqScore,
    candidates,
    selected: selectWithLimits(candidates, config),
  };
}

function calculateStats(rows: BacktestRow[]): BacktestStats {
  const completed = rows.filter(
    (row) =>
      typeof row.monthlyReturn === "number" &&
      typeof row.equity === "number" &&
      !row.provisional,
  );
  const returns = completed.map((row) => row.monthlyReturn as number);
  const equities = completed.map((row) => row.equity as number);

  if (!returns.length || !equities.length) {
    return {
      finalEquity: 1,
      cagr: 0,
      averageMonthlyReturn: 0,
      monthlyVolatility: 0,
      annualizedVolatility: 0,
      maxDrawdown: 0,
    };
  }

  let peak = equities[0];
  let maxDrawdown = 0;
  for (const equity of equities) {
    peak = Math.max(peak, equity);
    maxDrawdown = Math.min(maxDrawdown, equity / peak - 1);
  }

  const finalEquity = equities.at(-1) ?? 1;
  return {
    finalEquity,
    cagr: finalEquity > 0
      ? finalEquity ** (12 / returns.length) - 1
      : 0,
    averageMonthlyReturn: mean(returns),
    monthlyVolatility: stdev(returns),
    annualizedVolatility: stdev(returns) * Math.sqrt(12),
    maxDrawdown,
  };
}

export function buildDashboard(
  histories: Record<string, PricePoint[]>,
  tickers: TickerConfig[],
  config: StrategyConfig,
): DashboardPayload {
  const monthlyBySymbol = Object.fromEntries(
    Object.entries(histories).map(([symbol, history]) => [
      symbol,
      monthlyHistory(history),
    ]),
  );
  const monthMaps = Object.fromEntries(
    Object.entries(monthlyBySymbol).map(([symbol, points]) => [
      symbol,
      new Map(points.map((point) => [point.key, point.close])),
    ]),
  );

  const qqqMonths = monthlyBySymbol.QQQ;
  if (!qqqMonths || qqqMonths.length < 12) {
    throw new Error("QQQ price history is incomplete");
  }

  const latestIndex = qqqMonths.length - 1;
  const current = buildAtIndex({
    index: latestIndex,
    qqqMonths,
    monthMaps,
    histories,
    tickers,
    config,
    requireTradePrices: false,
  });

  if (!current) {
    throw new Error("Unable to calculate the current signal");
  }

  const allocationStatus =
    current.state === "Cash"
      ? "CashMarket"
      : current.selected.length < config.topN
        ? "CashInsufficient"
        : "Invest";
  const allocationCandidates = new Set(
    current.selected.map((candidate) => candidate.symbol),
  );
  const selectedSymbols =
    allocationStatus === "Invest" ? allocationCandidates : new Set<string>();
  const candidateMap = new Map(
    current.candidates.map((candidate, index) => [
      candidate.symbol,
      { candidate, rank: index + 1 },
    ]),
  );

  const momentum: MomentumRow[] = tickers
    .filter((ticker) => ticker.symbol !== "QQQ")
    .map((ticker) => {
      const ranked = candidateMap.get(ticker.symbol);
      const months = monthlyBySymbol[ticker.symbol] ?? [];
      const latest = months.at(-1);
      const one = months.at(-2);
      const three = months.at(-4);
      const six = months.at(-7);
      const m1 = latest && one ? latest.close / one.close - 1 : null;
      const m3 = latest && three ? latest.close / three.close - 1 : null;
      const m6 = latest && six ? latest.close / six.close - 1 : null;
      const score =
        m1 !== null && m3 !== null && m6 !== null
          ? config.weights.oneMonth * m1 +
            config.weights.threeMonth * m3 +
            config.weights.sixMonth * m6
          : null;
      const selected = selectedSymbols.has(ticker.symbol);

      let reason = "データ不足";
      if (m1 !== null && m1 >= config.surgeLimit) {
        reason = "1か月急騰を除外";
      } else if (score !== null && score <= current.qqqScore) {
        reason = "QQQスコア以下";
      } else if (ranked) {
        reason = selected
          ? "採用"
          : allocationStatus === "CashInsufficient" &&
              allocationCandidates.has(ticker.symbol)
            ? "候補不足のため現金"
            : "テーマ上限または順位";
      }

      return {
        symbol: ticker.symbol,
        genre: ticker.genre,
        current: latest?.close ?? null,
        oneMonth: m1,
        threeMonth: m3,
        sixMonth: m6,
        score,
        rank: ranked?.rank ?? null,
        eligible: Boolean(ranked),
        selected,
        reason,
      };
    })
    .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));

  const portfolio: PortfolioRow[] = momentum
    .filter((row) => row.selected)
    .map((row) => ({
      ...row,
      targetAmount: config.targetAmountUsd,
      targetShares:
        row.current && row.current > 0
          ? config.targetAmountUsd / row.current
          : null,
    }));

  const backtestRows: BacktestRow[] = [];
  let equity = 1;

  for (let index = 10; index < qqqMonths.length - 1; index += 1) {
    const signalMonth = toMonthEnd(qqqMonths[index].key);
    if (signalMonth < config.backtestStart) continue;

    const result = buildAtIndex({
      index,
      qqqMonths,
      monthMaps,
      histories,
      tickers,
      config,
      requireTradePrices: true,
    });
    if (!result) continue;

    if (result.state === "Cash") {
      backtestRows.push({
        signalMonth,
        entryDate: null,
        exitDate: toMonthEnd(qqqMonths[index + 1].key),
        market: "Cash",
        picks: [],
        monthlyReturn: 0,
        equity,
      });
      continue;
    }

    if (result.selected.length < config.topN) {
      backtestRows.push({
        signalMonth,
        entryDate: null,
        exitDate: toMonthEnd(qqqMonths[index + 1].key),
        market: "Not enough candidates",
        picks: [],
        monthlyReturn: 0,
        equity,
      });
      continue;
    }

    const provisional = result.selected.some(
      (candidate) =>
        candidate.provisional || candidate.nextReturn === null,
    );
    if (provisional) {
      backtestRows.push({
        signalMonth,
        entryDate: result.selected[0]?.entryDate ?? null,
        exitDate: null,
        market: "RiskOn",
        picks: result.selected.map((item) => item.symbol),
        monthlyReturn: null,
        equity: null,
        provisional: true,
      });
      continue;
    }

    const monthlyReturn = mean(
      result.selected.map((candidate) => candidate.nextReturn as number),
    );
    equity *= 1 + monthlyReturn;

    backtestRows.push({
      signalMonth,
      entryDate: result.selected[0]?.entryDate ?? null,
      exitDate: result.selected[0]?.exitDate ?? null,
      market: "RiskOn",
      picks: result.selected.map((item) => item.symbol),
      monthlyReturn,
      equity,
    });
  }

  return {
    source: "live",
    asOf: histories.QQQ.at(-1)?.date ?? qqqMonths.at(-1)?.date ?? "",
    market: {
      state: current.state,
      qqq: current.qqq,
      ma10: current.ma10,
      qqqScore: current.qqqScore,
      allocationStatus,
      selectedCount: current.selected.length,
    },
    momentum,
    portfolio,
    backtest: {
      rows: backtestRows,
      stats: calculateStats(backtestRows),
    },
    config,
  };
}
