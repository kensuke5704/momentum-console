import { readFile, mkdir, writeFile } from "node:fs/promises";

const raw=JSON.parse(await readFile("public/data/backtest-frozen.json","utf8"));
const bt=raw.backtest??raw;
const curve=bt.equityCurve??[];
if(curve.length<2) throw new Error("backtest equityCurve missing");
const rows=[];
for(let i=1;i<curve.length;i++) rows.push({date:curve[i].date,r:curve[i].equity/curve[i-1].equity-1});
const start=curve[0].date,end=curve.at(-1).date;
const years=(Date.parse(end)-Date.parse(start))/(365.25*86400000);
function simulate(exclude){let wealth=1,peak=1,dd=0;for(const x of rows){const r=exclude(x.date)?0:x.r;wealth*=1+r;peak=Math.max(peak,wealth);dd=Math.min(dd,wealth/peak-1)}return{finalEquity:wealth,cagr:wealth**(1/years)-1,maxDrawdown:dd}}
const baseline=simulate(()=>false);
const calendarYears=[...new Set(rows.map(x=>Number(x.date.slice(0,4))))];
const annual=calendarYears.map(y=>({year:y,...simulate(d=>Number(d.slice(0,4))===y)}));
const monthSet=[...new Set(rows.map(x=>x.date.slice(0,7)))];
const rolling=[];
for(let i=0;i<monthSet.length;i++){
  const sm=monthSet[i], sd=new Date(`${sm}-01T00:00:00Z`), ed=new Date(sd);ed.setUTCMonth(ed.getUTCMonth()+24);
  const endExclusive=ed.toISOString().slice(0,10);
  if(ed>Date.parse(end)) break;
  const s=simulate(d=>d>=`${sm}-01`&&d<endExclusive);
  rolling.push({startMonth:sm,endExclusive:endExclusive.slice(0,7),...s});
}
annual.sort((a,b)=>a.cagr-b.cagr); rolling.sort((a,b)=>a.cagr-b.cagr);
const result={generatedAt:new Date().toISOString(),strategyId:bt.strategyId,period:{start,end},method:"Set returns in the excluded period to 0 (cash) while preserving the original calendar horizon and all returns outside the period; no re-optimization.",baseline,annual,rolling24m:rolling};
await mkdir("data/research/period-jackknife",{recursive:true});
await writeFile("data/research/period-jackknife/result.json",JSON.stringify(result,null,2)+"\n");
const pct=x=>`${(x*100).toFixed(2)}%`;
let md=`# Period jackknife\n\nBaseline CAGR: **${pct(baseline.cagr)}** / MaxDD: **${pct(baseline.maxDrawdown)}**\n\n## Calendar-year exclusion (cash during excluded year)\n\n| Excluded year | CAGR | Δ CAGR | MaxDD | Final equity |\n|---:|---:|---:|---:|---:|\n`;
for(const x of annual) md+=`| ${x.year} | ${pct(x.cagr)} | ${pct(x.cagr-baseline.cagr)} | ${pct(x.maxDrawdown)} | ${x.finalEquity.toFixed(2)}x |\n`;
md+=`\n## Most influential rolling 24-month exclusions\n\n| Excluded window | CAGR | Δ CAGR | MaxDD | Final equity |\n|---|---:|---:|---:|---:|\n`;
for(const x of rolling.slice(0,12)) md+=`| ${x.startMonth} → ${x.endExclusive} | ${pct(x.cagr)} | ${pct(x.cagr-baseline.cagr)} | ${pct(x.maxDrawdown)} | ${x.finalEquity.toFixed(2)}x |\n`;
md+=`\n## Interpretation\n\nThis is a temporal concentration diagnostic, not a counterfactual market backtest: excluded-period strategy returns are replaced by cash returns of 0%, while the strategy's realized returns outside that window remain unchanged. Large CAGR drops identify periods that dominate the historical result.\n`;
await writeFile("data/research/period-jackknife/result.md",md);
console.log(md);console.log("RESULT_JSON="+JSON.stringify(result));
