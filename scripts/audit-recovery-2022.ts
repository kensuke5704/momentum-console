import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { qqqMonthlyGate } from "../src/lib/strategy/momentum";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history?: UniverseMonth[] };

type Row = {
  date: string;
  close: number;
  sma100: number | null;
  momentum20: number | null;
  aboveSma100: boolean;
  momentum20Positive: boolean;
  dailyRecoveryOk: boolean;
  rawDailyConsecutive: number;
  monthlySignalDate: boolean;
  monthlyGateRiskOn: boolean;
  monthlyGateClose: number | null;
  monthlyGateMa: number | null;
  effectiveRecoveryOk: boolean;
  effectiveConsecutive: number;
};

const START = "2021-12-02";
const END = "2023-02-14";

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universeFile = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const qqq = [...(market.histories?.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const universeHistory = [...(universeFile.history ?? [])].sort((a, b) => a.asOf.localeCompare(b.asOf));
  if (!qqq.length) throw new Error("QQQ history missing");
  if (!universeHistory.length) throw new Error("Universe history missing");

  const signalDates = new Set(universeHistory.map((u) => u.asOf));
  const smaDays = PRODUCTION_STRATEGY.recovery.qqqDailySmaDays;
  const momentumDays = PRODUCTION_STRATEGY.recovery.qqqMomentumDays;
  const confirmDays = PRODUCTION_STRATEGY.recovery.confirmationDays;

  let rawDailyConsecutive = 0;
  let effectiveConsecutive = 0;
  let marketRiskOn = false;
  let gateClose: number | null = null;
  let gateMa: number | null = null;
  const rows: Row[] = [];

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
    const dailyRecoveryOk = aboveSma100 && momentum20Positive;
    rawDailyConsecutive = dailyRecoveryOk ? rawDailyConsecutive + 1 : 0;

    const monthlySignalDate = signalDates.has(point.date);
    if (monthlySignalDate) {
      const gate = qqqMonthlyGate(qqq, point.date, PRODUCTION_STRATEGY);
      marketRiskOn = gate.riskOn;
      gateClose = gate.close;
      gateMa = gate.ma;
      if (!marketRiskOn) effectiveConsecutive = 0;
    }

    const effectiveRecoveryOk = marketRiskOn && dailyRecoveryOk;
    effectiveConsecutive = effectiveRecoveryOk ? effectiveConsecutive + 1 : 0;

    rows.push({
      date: point.date,
      close: point.close,
      sma100,
      momentum20,
      aboveSma100,
      momentum20Positive,
      dailyRecoveryOk,
      rawDailyConsecutive,
      monthlySignalDate,
      monthlyGateRiskOn: marketRiskOn,
      monthlyGateClose: gateClose,
      monthlyGateMa: gateMa,
      effectiveRecoveryOk,
      effectiveConsecutive,
    });
  }

  const during2022 = rows.filter((r) => r.date.startsWith("2022-"));
  const rawFirst10 = rows.find((r) => r.rawDailyConsecutive >= confirmDays) ?? null;
  const effectiveFirst10 = rows.find((r) => r.effectiveConsecutive >= confirmDays) ?? null;
  const gateChanges = rows.filter((r) => r.monthlySignalDate).map((r) => ({
    date: r.date,
    riskOn: r.monthlyGateRiskOn,
    qqqClose: r.monthlyGateClose,
    ma10: r.monthlyGateMa,
    effectiveConsecutive: r.effectiveConsecutive,
  }));
  const aroundRawFirst10 = rawFirst10 ? rows.slice(Math.max(0, rows.indexOf(rawFirst10) - 12), rows.indexOf(rawFirst10) + 1) : [];
  const aroundEffectiveFirst10 = effectiveFirst10 ? rows.slice(Math.max(0, rows.indexOf(effectiveFirst10) - 12), rows.indexOf(effectiveFirst10) + 1) : [];

  const summary = {
    parameters: { smaDays, momentumDays, confirmDays, monthlyMaMonths: PRODUCTION_STRATEGY.market.qqqMonthlyMaMonths },
    window: { start: START, end: END },
    rawDailyCondition: {
      maxConsecutiveIn2022: Math.max(0, ...during2022.map((r) => r.rawDailyConsecutive)),
      firstTenDayConfirmation: rawFirst10,
    },
    effectiveProductionCondition: {
      maxConsecutiveIn2022: Math.max(0, ...during2022.map((r) => r.effectiveConsecutive)),
      firstTenDayConfirmation: effectiveFirst10,
    },
    monthlyGateSignals: gateChanges,
    aroundRawFirstTen: aroundRawFirst10,
    aroundEffectiveFirstTen: aroundEffectiveFirst10,
    checks: {
      usesOnlyDataThroughSameClose: true,
      smaIncludesCurrentClose: true,
      momentumPriorIndex: `current index - ${momentumDays}`,
      monthlyGateUpdatedOnlyOnUniverseSignalDates: true,
      monthlyGateAppliedBeforeRecoveryCounterSameDay: true,
      resetOnAnyDailyFailureOrRiskOff: true,
    },
  };

  const out = resolve("data/research/recovery-audit-2022.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify({ summary, rows }, null, 2)}\n`);
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
