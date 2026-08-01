import { readFileSync } from "node:fs";
import { join } from "node:path";
import { MomentumApp } from "@/components/momentum-app";
import { DEFAULT_STRATEGY, TICKERS } from "@/lib/config";
import { buildDashboard } from "@/lib/momentum";
import { SNAPSHOT_DASHBOARD } from "@/lib/snapshot";
import type { DashboardPayload, PricePoint } from "@/lib/types";

function getInitialDashboard(): DashboardPayload {
  try {
    const marketDataPath = join(
      process.cwd(),
      "public",
      "data",
      "market-data.json",
    );
    const marketData = JSON.parse(
      readFileSync(marketDataPath, "utf8"),
    ) as {
      dashboard?: DashboardPayload;
      histories?: Record<string, PricePoint[]>;
    };

    if (marketData.histories?.QQQ?.length) {
      return buildDashboard(
        marketData.histories,
        TICKERS,
        marketData.dashboard?.config ?? DEFAULT_STRATEGY,
      );
    }

    return marketData.dashboard ?? SNAPSHOT_DASHBOARD;
  } catch {
    return SNAPSHOT_DASHBOARD;
  }
}

export default function Home() {
  return <MomentumApp initialDashboard={getInitialDashboard()} />;
}
