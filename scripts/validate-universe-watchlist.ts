import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { z } from "zod";
import { TICKERS } from "../src/lib/config";

const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "expected YYYY-MM-DD");

const forwardEvidenceSchema = z.object({
  startDate: isoDate,
  completedObservations: z.number().int().nonnegative(),
});

const sanityCheckSchema = z.object({
  selectedMonths: z.number().int().nonnegative(),
  changedMonths: z.number().int().nonnegative(),
  cagr: z.number(),
  deltaCagr: z.number(),
  maxDrawdown: z.number(),
  annualizedVolatility: z.number().nonnegative(),
  calmar: z.number(),
});

const candidateSchema = z.object({
  symbol: z.string().regex(/^[A-Z0-9.^=-]{1,15}$/),
  genre: z.string().min(1),
  track: z.literal("candidate"),
  priority: z.enum(["A", "B", "C"]),
  status: z.enum(["watch", "adopted", "rejected"]),
  discoveryDate: isoDate,
  rationale: z.string().min(1),
  sanityCheck: sanityCheckSchema,
  forwardEvidence: forwardEvidenceSchema,
});

const legacyReviewSchema = z.object({
  symbol: z.string().regex(/^[A-Z0-9.^=-]{1,15}$/),
  genre: z.string().min(1),
  track: z.literal("legacy-review"),
  priority: z.null(),
  status: z.enum(["review", "removed", "cleared"]),
  reviewDate: isoDate,
  rationale: z.string().min(1),
  legacyAudit: z.object({
    classification: z.enum(["A", "B", "C", "D"]),
    effectiveWindow: z.object({
      start: isoDate,
      end: isoDate,
    }),
    selectedMonths: z.number().int().nonnegative(),
    winRate: z.number().min(0).max(1),
    averageSelectedHoldingReturn: z.number(),
  }),
  forwardEvidence: forwardEvidenceSchema,
});

const watchlistSchema = z.object({
  version: z.literal(1),
  updatedAt: isoDate,
  policy: z.literal("docs/universe-governance.md"),
  purpose: z.string().min(1),
  sanityCheckContext: z.object({
    strategyId: z.string().min(1),
    baselineCagr: z.number(),
    baselineMaxDrawdown: z.number(),
    baselineAnnualizedVolatility: z.number().nonnegative(),
    baselineCalmar: z.number(),
    note: z.string().min(1),
  }),
  entries: z.array(z.discriminatedUnion("track", [candidateSchema, legacyReviewSchema])),
});

async function main() {
  const path = resolve("data/universe-watchlist.json");
  const raw = await readFile(path, "utf8");
  const watchlist = watchlistSchema.parse(JSON.parse(raw));

  const universeBySymbol = new Map(
    TICKERS.filter((ticker) => ticker.symbol !== "QQQ").map((ticker) => [
      ticker.symbol,
      ticker,
    ]),
  );
  const seen = new Set<string>();

  for (const entry of watchlist.entries) {
    if (seen.has(entry.symbol)) {
      throw new Error(`Duplicate watchlist symbol: ${entry.symbol}`);
    }
    seen.add(entry.symbol);

    const universeTicker = universeBySymbol.get(entry.symbol);

    if (entry.track === "candidate") {
      if (entry.status !== "adopted" && universeTicker) {
        throw new Error(
          `${entry.symbol}: candidate with status=${entry.status} is already in the production Universe`,
        );
      }
      if (entry.sanityCheck.changedMonths > entry.sanityCheck.selectedMonths) {
        throw new Error(
          `${entry.symbol}: changedMonths cannot exceed selectedMonths`,
        );
      }
      continue;
    }

    if (entry.status !== "removed" && !universeTicker) {
      throw new Error(
        `${entry.symbol}: legacy-review entry must exist in the production Universe unless status=removed`,
      );
    }
    if (universeTicker && universeTicker.genre !== entry.genre) {
      throw new Error(
        `${entry.symbol}: watchlist genre=${entry.genre} does not match Universe genre=${universeTicker.genre}`,
      );
    }
  }

  const candidateCount = watchlist.entries.filter(
    (entry) => entry.track === "candidate",
  ).length;
  const legacyReviewCount = watchlist.entries.filter(
    (entry) => entry.track === "legacy-review",
  ).length;

  console.log(
    `Universe watchlist valid: ${candidateCount} candidates, ${legacyReviewCount} legacy reviews`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
