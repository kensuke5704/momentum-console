import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/research/fixed60-falsification-core/result.json"
OUTDIR = ROOT / "data/research/fixed60-after-tax-density"
OUTDIR.mkdir(parents=True, exist_ok=True)

N_PATHS = 100
YEARS = 10
SESSIONS_PER_YEAR = 252
BLOCK = 63
ANNUAL_WITHDRAWAL = 0.075
SEED = 20260831
SAMPLE_STEP = 21
DISPLAY_FLOOR = 0.1
DISPLAY_CEILING = 1000.0

with INPUT.open() as f:
    result = json.load(f)

curve = result["baseline"]["afterTaxCurve"]
if len(curve) < BLOCK + 2:
    raise RuntimeError("After-tax curve is too short for the requested block bootstrap.")

equity = np.array([float(p["equity"]) for p in curve], dtype=float)
dates = [p["date"] for p in curve]
log_returns = np.diff(np.log(equity))

rng = np.random.default_rng(SEED)
n_sessions = YEARS * SESSIONS_PER_YEAR
paths = np.empty((N_PATHS, n_sessions + 1), dtype=float)
paths[:, 0] = 1.0

max_start = len(log_returns) - BLOCK
for i in range(N_PATHS):
    sampled = []
    while len(sampled) < n_sessions:
        start = int(rng.integers(0, max_start + 1))
        sampled.extend(log_returns[start:start + BLOCK])
    sampled = np.asarray(sampled[:n_sessions], dtype=float)
    wealth = 1.0
    for t, r in enumerate(sampled, start=1):
        wealth *= float(np.exp(r))
        if t % SESSIONS_PER_YEAR == 0:
            wealth -= ANNUAL_WITHDRAWAL
        wealth = max(wealth, 1e-6)
        paths[i, t] = wealth

sample_idx = np.unique(np.r_[np.arange(0, n_sessions + 1, SAMPLE_STEP), n_sessions])
times = sample_idx / SESSIONS_PER_YEAR
sampled_paths = paths[:, sample_idx]

log_min = np.log10(DISPLAY_FLOOR)
log_max = np.log10(DISPLAY_CEILING)
y_edges_log = np.linspace(log_min, log_max, 260)
y_edges = 10 ** y_edges_log
y_centers_log = 0.5 * (y_edges_log[:-1] + y_edges_log[1:])

hist = np.zeros((len(times), len(y_centers_log)), dtype=float)
for j in range(len(times)):
    vals = np.log10(np.clip(sampled_paths[:, j], DISPLAY_FLOOR, DISPLAY_CEILING))
    h, _ = np.histogram(vals, bins=y_edges_log)
    hist[j] = h

smooth = gaussian_filter(hist, sigma=(1.4, 2.2), mode="nearest")
if smooth.max() > 0:
    smooth /= smooth.max()

p05 = np.quantile(sampled_paths, 0.05, axis=0)
p50 = np.quantile(sampled_paths, 0.50, axis=0)
p95 = np.quantile(sampled_paths, 0.95, axis=0)

fig, ax = plt.subplots(figsize=(10, 10.5), dpi=180)
mesh = ax.pcolormesh(times, y_edges[:-1], smooth.T, shading="auto", cmap="viridis", vmin=0, vmax=1)
ax.plot(times, p95, linewidth=1.5, label="95th percentile")
ax.plot(times, p50, linewidth=2.3, label="50th percentile")
ax.plot(times, p05, linewidth=1.5, label="5th percentile")
ax.set_yscale("log")
ax.set_xlim(0, YEARS)
ax.set_ylim(DISPLAY_FLOOR, DISPLAY_CEILING)
ax.set_xticks(np.arange(0, YEARS + 1, 1))
ax.set_xlabel("Years")
ax.set_ylabel("Wealth multiple (log scale)")
ax.grid(True, which="major", axis="both", alpha=0.25)
ax.set_title(
    "100-Path Density Gradient (After-Tax Fixed60)\n"
    "Initial investment = 1, annual withdrawal = 0.075",
    pad=10,
)

cbar = fig.colorbar(mesh, ax=ax, pad=0.045)
cbar.set_label("Relative path density")
cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])

fig.text(
    0.5,
    0.015,
    f"Source: Fixed60 after-tax curve {dates[0]} to {dates[-1]} | tax 20.315% annual realized P&L approximation | "
    f"63-session moving-block bootstrap | seed {SEED}",
    ha="center",
    fontsize=8,
)
fig.tight_layout(rect=(0, 0.035, 1, 1))

png = OUTDIR / "fixed60-after-tax-100-path-density-20260831.png"
fig.savefig(png, bbox_inches="tight")
plt.close(fig)

metadata = {
    "generatedFrom": {
        "curveStart": dates[0],
        "curveEnd": dates[-1],
        "afterTaxStats": result["baseline"]["afterTax"],
        "taxApproximation": result["validity"]["taxApproximation"],
    },
    "simulation": {
        "paths": N_PATHS,
        "years": YEARS,
        "sessionsPerYear": SESSIONS_PER_YEAR,
        "blockSessions": BLOCK,
        "initialInvestment": 1.0,
        "annualWithdrawal": ANNUAL_WITHDRAWAL,
        "withdrawalTiming": "end of each simulated 252-session year",
        "seed": SEED,
    },
    "terminalWealth": {
        "p05": float(np.quantile(paths[:, -1], 0.05)),
        "median": float(np.quantile(paths[:, -1], 0.50)),
        "p95": float(np.quantile(paths[:, -1], 0.95)),
        "min": float(np.min(paths[:, -1])),
        "max": float(np.max(paths[:, -1])),
        "shareBelow1": float(np.mean(paths[:, -1] < 1.0)),
    },
}
with (OUTDIR / "metadata.json").open("w") as f:
    json.dump(metadata, f, indent=2)

print(json.dumps(metadata, indent=2))
print(str(png))
