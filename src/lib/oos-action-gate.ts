import type { ForwardOosResult } from "./types";

export type OosGateLevel = "GREEN" | "AMBER" | "RED";

export type OosActionGate = {
  level: OosGateLevel;
  phase: "WAITING" | "WARMUP" | "12M" | "24M" | "36M_PLUS";
  monthsObserved: number;
  instruction: string;
  reason: string;
  blocksNewEntries: boolean;
};

function calendarMonthsElapsed(start: string, end: string) {
  const [sy, sm, sd] = start.slice(0, 10).split("-").map(Number);
  const [ey, em, ed] = end.slice(0, 10).split("-").map(Number);
  let months = (ey - sy) * 12 + (em - sm);
  if (ed < sd) months -= 1;
  return Math.max(0, months);
}

function phaseFor(months: number, hasObservation: boolean): OosActionGate["phase"] {
  if (!hasObservation) return "WAITING";
  if (months < 12) return "WARMUP";
  if (months < 24) return "12M";
  if (months < 36) return "24M";
  return "36M_PLUS";
}

export function evaluateOosActionGate(oos: ForwardOosResult): OosActionGate {
  const hasObservation = Boolean(oos.asOf);
  const monthsObserved = hasObservation ? calendarMonthsElapsed(oos.startedAt, oos.asOf!) : 0;
  const phase = phaseFor(monthsObserved, hasObservation);
  const maxDrawdown = oos.stats.maxDrawdown;
  const cagr = oos.stats.cagr;

  // RED is a strategy-level kill switch. Once triggered, do not reinterpret or
  // retune the rule from the same OOS sample before deciding whether to restart.
  if (maxDrawdown <= -0.40) {
    return {
      level: "RED",
      phase,
      monthsObserved,
      instruction: "新規買付を停止。保有中なら次の米国寄付きで全売却し、Cashへ移行。",
      reason: `OOS MaxDD ${Math.abs(maxDrawdown * 100).toFixed(1)}% が40%のKill基準に到達しました。`,
      blocksNewEntries: true,
    };
  }

  if (monthsObserved >= 12 && cagr < 0 && maxDrawdown <= -0.30) {
    return {
      level: "RED",
      phase,
      monthsObserved,
      instruction: "新規買付を停止。保有中なら次の米国寄付きで全売却し、Cashへ移行。",
      reason: `12か月以上のOOSでCAGRがマイナス、かつMaxDDが30%超です。`,
      blocksNewEntries: true,
    };
  }

  // The preregistered 24M/36M gates use the live gross (pre-tax) OOS CAGR.
  if (monthsObserved >= 36 && cagr < 0.30) {
    return {
      level: "RED",
      phase,
      monthsObserved,
      instruction: "新規買付を停止。保有中なら次の米国寄付きで全売却し、Cashへ移行。",
      reason: `36か月以上の税引前OOS CAGRが30%未満です。`,
      blocksNewEntries: true,
    };
  }
  if (monthsObserved >= 24 && cagr < 0.20) {
    return {
      level: "RED",
      phase,
      monthsObserved,
      instruction: "新規買付を停止。保有中なら次の米国寄付きで全売却し、Cashへ移行。",
      reason: `24か月以上の税引前OOS CAGRが20%未満です。`,
      blocksNewEntries: true,
    };
  }

  if (maxDrawdown <= -0.30) {
    return {
      level: "AMBER",
      phase,
      monthsObserved,
      instruction: "取引ルールは変更せず継続。新規最適化はせず、OOSレビュー対象として扱う。",
      reason: `OOS MaxDD ${Math.abs(maxDrawdown * 100).toFixed(1)}% が30%のReview基準に到達しています。`,
      blocksNewEntries: false,
    };
  }

  if (!hasObservation) {
    return {
      level: "GREEN",
      phase,
      monthsObserved,
      instruction: "Fixed60のNext Actionに従う。OOS観測開始後もルールを固定して継続。",
      reason: "True Forward OOSの観測値はまだありません。性能評価ではなく実装整合性を確認する段階です。",
      blocksNewEntries: false,
    };
  }

  if (monthsObserved < 3) {
    return {
      level: "GREEN",
      phase,
      monthsObserved,
      instruction: "Fixed60のNext Actionに従う。CAGRで判断せず、執行・シグナル整合性を確認。",
      reason: "OOS開始3か月未満はCAGR評価を行いません。MaxDDのKill/Review基準のみ即時監視します。",
      blocksNewEntries: false,
    };
  }

  return {
    level: "GREEN",
    phase,
    monthsObserved,
    instruction: "Fixed60のNext Actionに従い、ルール変更なしで継続。",
    reason: "事前固定したOOS Kill Criteriaには抵触していません。",
    blocksNewEntries: false,
  };
}
