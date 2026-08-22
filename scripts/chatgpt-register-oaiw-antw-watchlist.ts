import fs from "node:fs";

const path = "data/universe-watchlist.json";
const data = JSON.parse(fs.readFileSync(path, "utf8"));
const existing = new Set(data.entries.map((e:any)=>e.symbol));
const discoveryDate = "2026-08-22";
const rows = [
  {symbol:"AMD",genre:"AI Semi",priority:"A",rationale:"AI accelerator and rack-scale compute candidate with direct OpenAI and Anthropic ecosystem relevance; monitor forward evidence under the frozen Momentum strategy.",sanityCheck:{selectedMonths:5,changedMonths:5,cagr:1.2655179376193475,deltaCagr:-0.011155263878661614,maxDrawdown:-0.20957952668156976,annualizedVolatility:0.5354023941977825,calmar:6.038366235754249}},
  {symbol:"AVGO",genre:"AI Semi",priority:"A",rationale:"Custom AI accelerator and networking candidate with direct Anthropic/OpenAI ecosystem exposure; historical evidence is limited but structurally relevant.",sanityCheck:{selectedMonths:2,changedMonths:2,cagr:1.2672908651918346,deltaCagr:-0.009382336306174466,maxDrawdown:-0.2112602904457732,annualizedVolatility:0.5333086019862799,calmar:5.998717802185006}},
  {symbol:"WULF",genre:"AI Infrastructure",priority:"A",rationale:"AI/HPC infrastructure transition candidate with long-duration Anthropic-related capacity contracts; historical mining-era behavior requires forward regime confirmation.",sanityCheck:{selectedMonths:20,changedMonths:20,cagr:1.323609302947085,deltaCagr:0.046936101449075895,maxDrawdown:-0.3162352489160595,annualizedVolatility:0.5435928779253558,calmar:4.1855210874940125}},
  {symbol:"HUT",genre:"AI Infrastructure",priority:"A",rationale:"AI data-center infrastructure transition candidate with Anthropic ecosystem relevance; retain for forward monitoring despite high historical drawdown and volatility.",sanityCheck:{selectedMonths:18,changedMonths:18,cagr:1.280404530030284,deltaCagr:0.003731328532274869,maxDrawdown:-0.27829336178952835,annualizedVolatility:0.5554796149567227,calmar:4.6009165356903}},
  {symbol:"IREN",genre:"AI Infrastructure",priority:"B",rationale:"Power-backed AI cloud and data-center infrastructure candidate with large-scale hyperscaler demand exposure; mining-era history limits retrospective interpretation.",sanityCheck:{selectedMonths:21,changedMonths:21,cagr:1.3414660835257481,deltaCagr:0.06479288202773903,maxDrawdown:-0.2980081978266599,annualizedVolatility:0.5417806028020564,calmar:4.50144020637321}},
  {symbol:"ORCL",genre:"AI Infrastructure",priority:"B",rationale:"Large-scale AI cloud infrastructure and Stargate ecosystem candidate; monitor forward evidence despite limited and weak retrospective selections.",sanityCheck:{selectedMonths:2,changedMonths:2,cagr:1.261300254532224,deltaCagr:-0.015372946965785061,maxDrawdown:-0.2112602904457732,annualizedVolatility:0.536192057700615,calmar:5.970361263211354}},
  {symbol:"CORZ",genre:"AI Infrastructure",priority:"C",rationale:"AI/HPC data-center conversion candidate retained for forward observation; retrospective Momentum selections were weak and business transition remains material.",sanityCheck:{selectedMonths:8,changedMonths:8,cagr:1.2300986068053938,deltaCagr:-0.04657459469261527,maxDrawdown:-0.2322201987010588,annualizedVolatility:0.5196849436392367,calmar:5.297121497983565}}
];
for (const r of rows) {
  if (existing.has(r.symbol)) throw new Error(`${r.symbol} already exists in watchlist`);
  data.entries.push({symbol:r.symbol,genre:r.genre,track:"candidate",priority:r.priority,status:"watch",discoveryDate,rationale:r.rationale,sanityCheck:r.sanityCheck,forwardEvidence:{startDate:discoveryDate,completedObservations:0}});
}
data.updatedAt = discoveryDate;
fs.writeFileSync(path, JSON.stringify(data,null,2)+"\n");
