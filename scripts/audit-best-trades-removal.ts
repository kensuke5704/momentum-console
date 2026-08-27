import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

type Trade = {
  symbol: string;
  entryDate: string;
  exitDate: string;
  grossAllocation: number;
  netProceeds: number;
  pnl: number;
  returnOnAllocation: number;
};
type Attribution = {
  period: { start: string; end: string };
  allTrades: Trade[];
};

type Episode = {
  key: string;
  entryDate: string;
  exitDate: string;
  trades: Trade[];
  grossAllocation: number;
  netProceeds: number;
  multiplier: number;
};

function daysBetween(a: string, b: string) {
  return (Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000;
}

function cagr(finalEquity: number, start: string, end: string) {
  const years = daysBetween(start, end) / 365.25;
  return Math.pow(finalEquity, 1 / years) - 1;
}

function buildEpisodes(trades: Trade[]): Episode[] {
  const grouped = new Map<string, Trade[]>();
  for (const t of trades) {
    const key = `${t.entryDate}|${t.exitDate}`;
    const rows = grouped.get(key) ?? [];
    rows.push(t);
    grouped.set(key, rows);
  }
  return [...grouped.entries()]
    .map(([key, rows]) => {
      const grossAllocation = rows.reduce((s, t) => s + t.grossAllocation, 0);
      const netProceeds = rows.reduce((s, t) => s + t.netProceeds, 0);
      return {
        key,
        entryDate: rows[0].entryDate,
        exitDate: rows[0].exitDate,
        trades: rows,
        grossAllocation,
        netProceeds,
        multiplier: grossAllocation ? netProceeds / grossAllocation : 1,
      };
    })
    .sort((a, b) => a.entryDate.localeCompare(b.entryDate) || a.exitDate.localeCompare(b.exitDate));
}

function finalEquityWithRemoved(episodes: Episode[], removed: Set<string>) {
  let equity = 1;
  const curve: Array<{ date: string; equity: number }> = [];
  for (const ep of episodes) {
    const stressedNet = ep.trades.reduce((sum, t, idx) => {
      const id = `${t.symbol}|${t.entryDate}|${t.exitDate}|${idx}`;
      return sum + (removed.has(id) ? t.grossAllocation : t.netProceeds);
    }, 0);
    const multiplier = ep.grossAllocation ? stressedNet / ep.grossAllocation : 1;
    equity *= multiplier;
    curve.push({ date: ep.exitDate, equity });
  }
  let peak = 1;
  let maxDrawdown = 0;
  for (const point of curve) {
    peak = Math.max(peak, point.equity);
    maxDrawdown = Math.min(maxDrawdown, point.equity / peak - 1);
  }
  return { finalEquity: equity, episodeBoundaryMaxDrawdown: maxDrawdown };
}

async function main() {
  const input = JSON.parse(await readFile(resolve("data/research/trade-attribution.json"), "utf8")) as Attribution;
  const episodes = buildEpisodes(input.allTrades);
  const baseline = finalEquityWithRemoved(episodes, new Set());

  const ranked = input.allTrades
    .map((t, index) => ({ ...t, id: `${t.symbol}|${t.entryDate}|${t.exitDate}|${index}` }))
    .filter((t) => t.pnl > 0)
    .sort((a, b) => b.pnl - a.pnl);

  // IDs in the replay below must correspond to each trade's index inside its episode, not global index.
  const episodeIds = new Map<string, string>();
  for (const ep of episodes) {
    ep.trades.forEach((t, idx) => episodeIds.set(`${t.symbol}|${t.entryDate}|${t.exitDate}|${t.pnl.toPrecision(15)}`, `${t.symbol}|${t.entryDate}|${t.exitDate}|${idx}`));
  }
  const rankedWithEpisodeId = ranked.map((t) => ({ ...t, episodeId: episodeIds.get(`${t.symbol}|${t.entryDate}|${t.exitDate}|${t.pnl.toPrecision(15)}`)! }));

  const counts = [1, 3, 5, Math.max(1, Math.ceil(rankedWithEpisodeId.length * 0.10))];
  const labels = ["TOP_1", "TOP_3", "TOP_5", "TOP_10PCT_WINNERS"];
  const scenarios = counts.map((count, i) => {
    const removedTrades = rankedWithEpisodeId.slice(0, count);
    const stressed = finalEquityWithRemoved(episodes, new Set(removedTrades.map((t) => t.episodeId)));
    return {
      label: labels[i],
      removedCount: count,
      removedTrades: removedTrades.map(({ symbol, entryDate, exitDate, pnl, returnOnAllocation }) => ({ symbol, entryDate, exitDate, pnl, returnOnAllocation })),
      finalEquity: stressed.finalEquity,
      cagr: cagr(stressed.finalEquity, input.period.start, input.period.end),
      episodeBoundaryMaxDrawdown: stressed.episodeBoundaryMaxDrawdown,
      finalEquityRatioVsBaseline: stressed.finalEquity / baseline.finalEquity,
    };
  });

  const output = {
    generatedAt: new Date().toISOString(),
    period: input.period,
    method: "Hindsight fixed-path excision stress. Baseline entry/exit dates, selected symbols, risk-state path, and all other trade returns are held fixed. For removed winning lots only, net proceeds are replaced by entry gross allocation (0% return), then episode multipliers are recompounded. This is a robustness stress test, not a tradable or causal counterfactual. MaxDD is measured only at episode boundaries.",
    baseline: {
      finalEquity: baseline.finalEquity,
      cagr: cagr(baseline.finalEquity, input.period.start, input.period.end),
      episodeBoundaryMaxDrawdown: baseline.episodeBoundaryMaxDrawdown,
      winningLots: rankedWithEpisodeId.length,
    },
    scenarios,
  };

  const out = resolve("data/research/best-trades-removal.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(output, null, 2)}\n`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });