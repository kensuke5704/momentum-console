import { readFileSync } from "node:fs";
import { join } from "node:path";
import { MomentumApp } from "@/components/momentum-app";
import { SNAPSHOT_DASHBOARD } from "@/lib/snapshot";
import type { DashboardPayload } from "@/lib/types";

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
    ) as { dashboard?: DashboardPayload };

    return marketData.dashboard ?? SNAPSHOT_DASHBOARD;
  } catch {
    return SNAPSHOT_DASHBOARD;
  }
}

export default function Home() {
  return <MomentumApp initialDashboard={getInitialDashboard()} />;
}
