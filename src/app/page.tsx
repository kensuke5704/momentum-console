import { readFileSync } from "node:fs";
import { join } from "node:path";
import { MomentumApp } from "@/components/momentum-app";
import { SNAPSHOT_DASHBOARD } from "@/lib/snapshot";
import type { DashboardPayload } from "@/lib/types";

function initialDashboard(): DashboardPayload {
  try {
    const data = JSON.parse(readFileSync(join(process.cwd(), "public/data/dashboard.json"), "utf8")) as { dashboard?: DashboardPayload };
    return data.dashboard?.config?.strategyId ? data.dashboard : SNAPSHOT_DASHBOARD;
  } catch { return SNAPSHOT_DASHBOARD; }
}
export default function Home() { return <MomentumApp initialDashboard={initialDashboard()} />; }
