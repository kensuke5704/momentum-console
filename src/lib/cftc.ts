import {PRODUCTION_PORTFOLIO} from "./portfolio-config";

export type CftcPositionRow = { reportDate: string; net: number };
export type CftcStatus = { reportDate: string | null; net: number | null; priorNet: number | null; yellow: boolean };

// 2025 US-government shutdown delayed publication of these reports. Historical
// backtests must use the actual release date instead of treating reportDate as
// publicationDate. Normal weeks retain the frozen seven-day conservative lag.
const RELEASE_OVERRIDES: Record<string,string> = {
  "2025-09-30":"2025-11-19","2025-10-07":"2025-11-21","2025-10-14":"2025-11-25",
  "2025-10-21":"2025-12-02","2025-10-28":"2025-12-05","2025-11-04":"2025-12-09",
  "2025-11-10":"2025-12-10","2025-11-18":"2025-12-12","2025-11-25":"2025-12-15",
  "2025-12-02":"2025-12-17","2025-12-09":"2025-12-19","2025-12-16":"2025-12-23",
  "2025-12-23":"2025-12-29",
};

export async function fetchNasdaqAssetManagerPositions(): Promise<CftcPositionRow[]> {
  const code = PRODUCTION_PORTFOLIO.cftc.contractCode;
  const url = `https://publicreporting.cftc.gov/resource/gpe5-46if.json?$limit=5000&$where=cftc_contract_market_code='${code}'&$order=report_date_as_yyyy_mm_dd`;
  const response = await fetch(url, { headers: { "user-agent": "momentum-console/1.0" } });
  if (!response.ok) throw new Error(`CFTC positioning request failed: ${response.status}`);
  const rows = await response.json() as Array<Record<string,unknown>>;
  return rows.flatMap((row) => {
    const reportDate = String(row.report_date_as_yyyy_mm_dd ?? "").slice(0,10);
    const long = Number(row.asset_mgr_positions_long), short = Number(row.asset_mgr_positions_short);
    return reportDate && Number.isFinite(long) && Number.isFinite(short) ? [{reportDate,net:long-short}] : [];
  }).sort((a,b)=>a.reportDate.localeCompare(b.reportDate));
}

export function cftcStatus(rows:CftcPositionRow[], signalDate:string): CftcStatus {
  const cut = new Date(`${signalDate}T00:00:00Z`);
  cut.setUTCDate(cut.getUTCDate()-PRODUCTION_PORTFOLIO.cftc.publicationLagDays);
  const cutoff = cut.toISOString().slice(0,10);
  const eligible = rows.filter((row) => row.reportDate <= cutoff && (!RELEASE_OVERRIDES[row.reportDate] || RELEASE_OVERRIDES[row.reportDate] <= signalDate));
  const lookback = PRODUCTION_PORTFOLIO.cftc.lookbackReports;
  if (eligible.length < lookback + 1) return {reportDate:eligible.at(-1)?.reportDate??null,net:eligible.at(-1)?.net??null,priorNet:null,yellow:false};
  const latest = eligible.at(-1)!, prior = eligible.at(-(lookback+1))!;
  return {reportDate:latest.reportDate,net:latest.net,priorNet:prior.net,yellow:latest.net < prior.net};
}
