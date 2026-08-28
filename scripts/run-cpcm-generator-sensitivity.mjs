import { readFile, writeFile, unlink } from "node:fs/promises";
import { spawnSync } from "node:child_process";

const block = Number(process.env.CPCM_BLOCK ?? 20);
const radius = Number(process.env.CPCM_RADIUS ?? 126);
if (![10,20,40].includes(block)) throw new Error(`Unsupported CPCM_BLOCK=${block}`);
if (![63,126,252].includes(radius)) throw new Error(`Unsupported CPCM_RADIUS=${radius}`);

const sourcePath = new URL("./chronology-preserving-conditional-mc.ts", import.meta.url);
const tempPath = new URL(`./.cpcm-generator-b${block}-r${radius}.ts`, import.meta.url);
let source = await readFile(sourcePath, "utf8");
const needle = "WARM=252, BLOCK=20, RADIUS=126;";
if (!source.includes(needle)) throw new Error("CPCM source constants changed; refusing implicit patch");
source = source.replace(needle, `WARM=252, BLOCK=${block}, RADIUS=${radius};`);
source = source.replace(
  'parameters:{individualStop:STOP,recoveryDays:RECOVERY_DAYS,seed:SEED}',
  `parameters:{individualStop:STOP,recoveryDays:RECOVERY_DAYS,seed:SEED,blockTradingDays:${block},radiusTradingDays:${radius}}`
);
source = source.replace(
  'donor:"20-day blocks sampled from +/-126 trading days, conditioned on QQQ 60d trend sign/proximity and 20d volatility proximity"',
  `donor:"${block}-day blocks sampled from +/-${radius} trading days, conditioned on QQQ 60d trend sign/proximity and 20d volatility proximity"`
);
await writeFile(tempPath, source);
try {
  const result = spawnSync(process.execPath, ["--import", "tsx", tempPath.pathname], {
    stdio: "inherit",
    env: process.env,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
} finally {
  await unlink(tempPath).catch(() => {});
}
