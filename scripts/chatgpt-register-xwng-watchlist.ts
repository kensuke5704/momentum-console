import fs from "node:fs";

const path = "data/universe-watchlist.json";
const data = JSON.parse(fs.readFileSync(path, "utf8"));
const existing = new Set(data.entries.map((entry: any) => entry.symbol));
const discoveryDate = "2026-08-22";

const entries = [
  {
    symbol: "SPCX", genre: "Space", track: "candidate", priority: "A", status: "watch", discoveryDate,
    rationale: "Newly listed SpaceX candidate with direct launch, satellite communications, and space-transport exposure; historical Frozen Strategy evidence is unavailable due to insufficient post-listing lookback, so forward monitoring is the primary evidence path.",
    sanityCheck: { selectedMonths: 0, changedMonths: 0, cagr: 1.2766732321025644, deltaCagr: 0, maxDrawdown: -0.2112602904457732, annualizedVolatility: 0.534866951010999, calmar: 6.04312920998404 },
    forwardEvidence: { startDate: discoveryDate, completedObservations: 0 },
  },
  {
    symbol: "RDW", genre: "Space", track: "candidate", priority: "A", status: "watch", discoveryDate,
    rationale: "Space infrastructure and defense-technology candidate with backlog and commercialization exposure; historical Frozen Strategy selections exist without material drawdown deterioration, supporting forward monitoring.",
    sanityCheck: { selectedMonths: 4, changedMonths: 4, cagr: 1.239217635305708, deltaCagr: -0.037455596796856394, maxDrawdown: -0.21126029044577332, annualizedVolatility: 0.5331370735556209, calmar: 5.865833246233242 },
    forwardEvidence: { startDate: discoveryDate, completedObservations: 0 },
  },
  {
    symbol: "MDA", genre: "Space", track: "candidate", priority: "A", status: "watch", discoveryDate,
    rationale: "Space systems candidate spanning satellite communications, earth/space observation, and space robotics; U.S. listing history is too short for meaningful Frozen Strategy selection evidence, making forward monitoring especially informative.",
    sanityCheck: { selectedMonths: 0, changedMonths: 0, cagr: 1.2766732321025644, deltaCagr: 0, maxDrawdown: -0.2112602904457732, annualizedVolatility: 0.534866951010999, calmar: 6.04312920998404 },
    forwardEvidence: { startDate: discoveryDate, completedObservations: 0 },
  },
  {
    symbol: "SPIR", genre: "Space", track: "candidate", priority: "B", status: "watch", discoveryDate,
    rationale: "Satellite data, weather intelligence, and RF geolocation candidate with government and defense demand exposure; limited historical selections justify forward monitoring rather than adoption conclusions.",
    sanityCheck: { selectedMonths: 2, changedMonths: 2, cagr: 1.2372346355538006, deltaCagr: -0.039438596548763805, maxDrawdown: -0.2112602904457732, annualizedVolatility: 0.5322656089163613, calmar: 5.856446722397066 },
    forwardEvidence: { startDate: discoveryDate, completedObservations: 0 },
  },
  {
    symbol: "VSAT", genre: "Space", track: "candidate", priority: "B", status: "watch", discoveryDate,
    rationale: "Satellite communications candidate with direct space-network exposure and constructive selected-month historical behavior; retain for forward evidence under the frozen strategy.",
    sanityCheck: { selectedMonths: 6, changedMonths: 6, cagr: 1.247215695214829, deltaCagr: -0.029457536887735447, maxDrawdown: -0.20477054417676843, annualizedVolatility: 0.530225017438731, calmar: 6.0907964093613405 },
    forwardEvidence: { startDate: discoveryDate, completedObservations: 0 },
  },
];

for (const entry of entries) {
  if (!existing.has(entry.symbol)) data.entries.push(entry);
}

data.updatedAt = discoveryDate;
fs.writeFileSync(path, JSON.stringify(data, null, 2) + "\n");
