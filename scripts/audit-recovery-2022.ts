import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { PricePoint } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };

type Row = {
  date: string;
  close: number;
  sma100: number | null;
  momentum20: number | null;
  aboveSma100: boolean;
  momentum20Positive: boolean;
  recoveryOk: boolean;
  consecutive: number;
};

const START = "2021-12-02";
const END = "2023-02-14";

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const qqq = [...(market.histories?.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  if (!qqq.length) throw new Error("QQQ history missing");

  const smaDays = PRODUCTION_STRATEGY.recovery.qqqDailySmaDays;
  const momentumDays = PRODUCTION_STRATEGY.recovery.qqqMomentumDays;
  const confirmDays = PRODUCTION_STRATEGY.recovery.confirmationDays;

  let consecutive = 0;
  const rows: Row[] = [];
  const qualifyingRuns: { start: string; end: string; length: number }[] = [];
  let runStart: string | null = null;

  for (let i = 0; i < qqq.length; i++) {
    const point = qqq[i];
    if (point.date < START || point.date > END) continue;
    const through = qqq.slice(0, i + 1);
    const enough = through.length >= Math.max(smaDays, momentumDays + 1);
    const sma100 = enough ? through.slice(-smaDays).reduce((sum, p) => sum + p.close, 0) / smaDays : null;
    const prior = enough ? through.at(-(momentumDays + 1))?.close ?? null : null;
    const momentum20 = prior ? point.close / prior - 1 : null;
    const aboveSma100 = sma100 !== null && point.close > sma100;
    const momentum20Positive = momentum20 !== null && momentum20 > 0;
    const recoveryOk = aboveSma100 && momentum20Positive;

    if (recoveryOk) {
      if (!runStart) runStart = point.date;
      consecutive += 1;
    } else {
      if (runStart && consecutive > 0) qualifyingRuns.push({ start: runStart, end: rows.at(-1)?.date ?? point.date, length: consecutive });
      runStart = null;
      consecutive = 0;
    }

    rows.push({ date: point.date, close: point.close, sma100, momentum20, aboveSma100, momentum20Positive, recoveryOk, consecutive });
  }
  if (runStart && consecutive > 0) qualifyingRuns.push({ start: runStart, end: rows.at(-1)!.date, length: consecutive });

  const firstConfirm = rows.find((r) => r.consecutive >= confirmDays) ?? null;
  const during2022 = rows.filter((r) => r.date.startsWith("2022-"));
  const max2022 = Math.max(0, ...during2022.map((r) => r.consecutive));
  const first10In2022 = during2022.find((r) => r.consecutive >= confirmDays) ?? null;
  const aroundConfirm = firstConfirm ? rows.filter((r) => r.date >= rows[Math.max(0, rows.indexOf(firstConfirm) - 12)].date && r.date <= firstConfirm.date) : [];

  const summary = {
    parameters: { smaDays, momentumDays, confirmDays },
    window: { start: START, end: END },
    maxConsecutiveIn2022: max2022,
    firstTenDayConfirmationIn2022: first10In2022,
    firstTenDayConfirmationOverall: firstConfirm,
    qualifyingRuns,
    aroundFirstConfirmation: aroundConfirm,
    checks: {
      usesOnlyDataThroughSameClose: true,
      smaIncludesCurrentClose: true,
      momentumPriorIndex: `current index - ${momentumDays}`,
      resetOnAnyFailure: true,
    },
  };

  const out = resolve("data/research/recovery-audit-2022.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify({ summary, rows }, null, 2)}\n`);
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
