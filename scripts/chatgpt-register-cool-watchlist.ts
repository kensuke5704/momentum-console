import { readFile, writeFile, rm } from "node:fs/promises";
import { resolve } from "node:path";

async function main() {
  const path = resolve("data/universe-watchlist.json");
  const raw = await readFile(path, "utf8");
  const data = JSON.parse(raw);
  const additions = [
    {
      symbol: "NVTS",
      genre: "AI Semi",
      track: "candidate",
      priority: "A",
      status: "watch",
      discoveryDate: "2026-08-22",
      rationale: "GaN/SiC power-semiconductor candidate tied to next-generation AI data-center power delivery and higher-voltage rack architectures; monitor forward behavior under the frozen strategy.",
      sanityCheck: {
        selectedMonths: 8,
        changedMonths: 8,
        cagr: 1.2652632021032462,
        deltaCagr: -0.011409990546339621,
        maxDrawdown: -0.24853025173116416,
        annualizedVolatility: 0.5458135940131902,
        calmar: 5.0909826602191055
      },
      forwardEvidence: { startDate: "2026-08-22", completedObservations: 0 }
    },
    {
      symbol: "AEIS",
      genre: "AI Infrastructure",
      track: "candidate",
      priority: "B",
      status: "watch",
      discoveryDate: "2026-08-22",
      rationale: "Precision power-conversion candidate with direct exposure to higher-density AI data-center power architectures; historical fit is acceptable but forward evidence is required.",
      sanityCheck: {
        selectedMonths: 5,
        changedMonths: 5,
        cagr: 1.269546658919431,
        deltaCagr: -0.007126533730154705,
        maxDrawdown: -0.2112602904457732,
        annualizedVolatility: 0.5341652614234675,
        calmar: 6.009395595549942
      },
      forwardEvidence: { startDate: "2026-08-22", completedObservations: 0 }
    },
    {
      symbol: "NVT",
      genre: "AI Infrastructure",
      track: "candidate",
      priority: "B",
      status: "watch",
      discoveryDate: "2026-08-22",
      rationale: "Liquid-cooling and high-density power-distribution candidate serving AI/HPC data-center infrastructure; limited but constructive historical strategy selections justify forward monitoring.",
      sanityCheck: {
        selectedMonths: 3,
        changedMonths: 3,
        cagr: 1.2654677980925415,
        deltaCagr: -0.01120539455704428,
        maxDrawdown: -0.2112602904457732,
        annualizedVolatility: 0.5323758013809552,
        calmar: 5.990088319117239
      },
      forwardEvidence: { startDate: "2026-08-22", completedObservations: 0 }
    },
    {
      symbol: "VICR",
      genre: "AI Infrastructure",
      track: "candidate",
      priority: "C",
      status: "watch",
      discoveryDate: "2026-08-22",
      rationale: "High-density power-delivery candidate relevant to AI/HPC infrastructure; forward monitoring is warranted despite volatile historical selected-month behavior.",
      sanityCheck: {
        selectedMonths: 9,
        changedMonths: 9,
        cagr: 1.2404012107329363,
        deltaCagr: -0.03627198191664949,
        maxDrawdown: -0.2525942518605775,
        annualizedVolatility: 0.5495650980150217,
        calmar: 4.910647022235451
      },
      forwardEvidence: { startDate: "2026-08-22", completedObservations: 0 }
    }
  ];

  const existing = new Set(data.entries.map((entry: any) => entry.symbol));
  for (const addition of additions) {
    if (existing.has(addition.symbol)) throw new Error(`${addition.symbol} already exists in watchlist`);
    data.entries.push(addition);
  }
  data.updatedAt = "2026-08-22";
  await writeFile(path, JSON.stringify(data, null, 2) + "\n", "utf8");

  await rm(resolve("scripts/chatgpt-register-cool-watchlist.ts"), { force: true });
  await rm(resolve(".github/workflows/chatgpt-register-cool-watchlist.yml"), { force: true });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});