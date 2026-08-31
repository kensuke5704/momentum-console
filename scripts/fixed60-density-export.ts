import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";

async function main() {
  const root = process.cwd();
  const sourcePath = path.join(root, "scripts/fixed60-falsification-core.ts");
  const tempPath = path.join(root, "scripts/.fixed60-falsification-core-density.tmp.ts");
  const source = await fs.readFile(sourcePath, "utf8");
  const needle = "baseline:{gross:base.gross,afterTax:base.afterTax,taxPaidApprox:base.taxPaidApprox,sales:base.sales}";
  const replacement = "baseline:{gross:base.gross,afterTax:base.afterTax,afterTaxCurve:base.afterTaxCurve,taxPaidApprox:base.taxPaidApprox,sales:base.sales}";
  if (!source.includes(needle)) throw new Error("Could not locate Fixed60 baseline output block.");
  await fs.writeFile(tempPath, source.replace(needle, replacement));
  try {
    const result = spawnSync("npx", ["tsx", tempPath], { cwd: root, stdio: "inherit" });
    if (result.status !== 0) throw new Error(`Fixed60 export failed with status ${result.status}`);
  } finally {
    await fs.rm(tempPath, { force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
