import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";

async function main() {
  const root = process.cwd();
  const sourcePath = path.join(root, "scripts/fixed60-falsification-core.ts");
  const tempPath = path.join(root, "scripts/.fixed60-falsification-core-density.tmp.ts");
  const source = await fs.readFile(sourcePath, "utf8");
  const marker = "async function main()";
  const markerIndex = source.indexOf(marker);
  if (markerIndex < 0) throw new Error("Could not locate Fixed60 main function.");
  const prefix = source.slice(0, markerIndex);
  const densityMain = `async function main(){
    const m=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8'))as{histories:Record<string,PricePoint[]>};
    const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8'))as{history:UniverseMonth[]};
    const u=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
    const base=sim(m.histories,u);
    const out={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,fixedAllocation:'60/40',taxApproximation:'20.315% annual realized P&L with 3-year loss carry; not exact broker tax lots/withholding.'},baseline:{gross:base.gross,afterTax:base.afterTax,afterTaxCurve:base.afterTaxCurve,taxPaidApprox:base.taxPaidApprox,sales:base.sales}};
    const d=path.join(process.cwd(),'data/research/fixed60-falsification-core');
    await fs.mkdir(d,{recursive:true});
    await fs.writeFile(path.join(d,'result.json'),JSON.stringify(out,null,2));
    console.log(JSON.stringify({generatedAt:out.generatedAt,afterTax:out.baseline.afterTax,curveStart:base.afterTaxCurve.at(0)?.date,curveEnd:base.afterTaxCurve.at(-1)?.date,points:base.afterTaxCurve.length},null,2));
  }
  main().catch(e=>{console.error(e);process.exit(1)});`;
  await fs.writeFile(tempPath, prefix + densityMain);
  try {
    const result = spawnSync("npx", ["tsx", tempPath], { cwd: root, stdio: "inherit" });
    if (result.status !== 0) throw new Error(`Fixed60 baseline export failed with status ${result.status}`);
  } finally {
    await fs.rm(tempPath, { force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
