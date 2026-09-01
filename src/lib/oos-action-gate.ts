import type { ForwardOosResult } from "./types";

export type OosGateLevel = "GREEN" | "AMBER" | "RED";
export type OosActionGate = { level:OosGateLevel;phase:"WAITING"|"WARMUP"|"12M"|"24M"|"36M_PLUS";monthsObserved:number;instruction:string;reason:string;blocksNewEntries:boolean };

function calendarMonthsElapsed(start:string,end:string){const[sy,sm,sd]=start.slice(0,10).split("-").map(Number),[ey,em,ed]=end.slice(0,10).split("-").map(Number);let months=(ey-sy)*12+(em-sm);if(ed<sd)months-=1;return Math.max(0,months)}
function phaseFor(months:number,hasObservation:boolean):OosActionGate["phase"]{if(!hasObservation)return"WAITING";if(months<12)return"WARMUP";if(months<24)return"12M";if(months<36)return"24M";return"36M_PLUS"}

/** Stage21 rounded-v1 OOS gates frozen before the first production observation. */
export function evaluateOosActionGate(oos:ForwardOosResult):OosActionGate{
 const hasObservation=Boolean(oos.asOf),monthsObserved=hasObservation?calendarMonthsElapsed(oos.startedAt,oos.asOf!):0,phase=phaseFor(monthsObserved,hasObservation),maxDrawdown=oos.stats.maxDrawdown,cagr=oos.stats.cagr;
 if(maxDrawdown<=-.25)return{level:"RED",phase,monthsObserved,instruction:"Stage21の新規買付を停止し、次の米国寄付きで全資産をCashへ移行。ルールを同じOOS標本で再調整しない。",reason:`OOS MaxDD ${Math.abs(maxDrawdown*100).toFixed(1)}% が25%のKill基準に到達しました。`,blocksNewEntries:true};
 if(monthsObserved>=12&&cagr<0&&maxDrawdown<=-.17)return{level:"RED",phase,monthsObserved,instruction:"Stage21の新規買付を停止し、次の米国寄付きでCashへ移行。",reason:"12か月以上のOOSでCAGRがマイナス、かつ研究上の17%DD境界を超えています。",blocksNewEntries:true};
 if(monthsObserved>=36&&cagr<.25)return{level:"RED",phase,monthsObserved,instruction:"Stage21の新規買付を停止し、長期OOSレビューへ移行。",reason:"36か月以上の税引前OOS CAGRが25%未満です。",blocksNewEntries:true};
 if(monthsObserved>=24&&cagr<.15)return{level:"RED",phase,monthsObserved,instruction:"Stage21の新規買付を停止し、長期OOSレビューへ移行。",reason:"24か月以上の税引前OOS CAGRが15%未満です。",blocksNewEntries:true};
 if(maxDrawdown<=-.17)return{level:"AMBER",phase,monthsObserved,instruction:"ルールを変更せず継続し、17% historical research gate超過としてレビュー。25% Killまでは自動停止しない。",reason:`OOS MaxDD ${Math.abs(maxDrawdown*100).toFixed(1)}% が17%のReview基準に到達しています。`,blocksNewEntries:false};
 if(!hasObservation)return{level:"GREEN",phase,monthsObserved,instruction:"Stage21のPortfolio Next Actionに従う。性能評価ではなくデータ・state・執行parityを確認。",reason:"Stage21 True Forward OOSの観測値はまだありません。",blocksNewEntries:false};
 if(monthsObserved<3)return{level:"GREEN",phase,monthsObserved,instruction:"Stage21のPortfolio Next Actionに従う。CAGRで判断せず、CFTC/M3/state/執行parityを確認。",reason:"OOS開始3か月未満はCAGR評価を行いません。DDのReview/Kill基準のみ即時監視します。",blocksNewEntries:false};
 return{level:"GREEN",phase,monthsObserved,instruction:"Stage21のPortfolio Next Actionに従い、ルール変更なしで継続。",reason:"事前固定したStage21 OOS基準には抵触していません。",blocksNewEntries:false};
}
