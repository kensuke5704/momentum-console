import fs from "node:fs/promises";
import path from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

const TAX_RATE = 0.20315;
const YEARS = 10;
const MONTHS = YEARS * 12;
const BLOCK_MONTHS = 3;
const PATHS = 50000;
const WITHDRAWAL = 0.075; // fixed fraction of initial capital, paid at each year-end after tax
const SEED = 20260830;

const cagrBins = [
  { lo: -0.10, hi: 0.00, p: 0.08, label: "<0%" },
  { lo: 0.00, hi: 0.10, p: 0.12, label: "0-10%" },
  { lo: 0.10, hi: 0.20, p: 0.21, label: "10-20%" },
  { lo: 0.20, hi: 0.30, p: 0.27, label: "20-30%" },
  { lo: 0.30, hi: 0.40, p: 0.18, label: "30-40%" },
  { lo: 0.40, hi: 0.50, p: 0.09, label: "40-50%" },
  { lo: 0.50, hi: 0.65, p: 0.05, label: ">=50% (capped at 65% for simulation)" },
];

function mulberry32(seed:number){return function(){let t=seed+=0x6D2B79F5;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;}}
const rng=mulberry32(SEED);
const q=(xs:number[],p:number)=>{const a=[...xs].sort((x,y)=>x-y);const i=(a.length-1)*p,lo=Math.floor(i),hi=Math.ceil(i);return lo===hi?a[lo]:a[lo]*(hi-i)+a[hi]*(i-lo)};
function sampleTargetCagr(){const u=rng();let c=0;for(const b of cagrBins){c+=b.p;if(u<=c)return b.lo+rng()*(b.hi-b.lo);}return 0.50+rng()*0.15;}
function monthKey(d:string){return d.slice(0,7)}
function monthlyLogReturns(curve:{date:string;equity:number}[]){const monthLast=new Map<string,{date:string;equity:number}>();for(const p of curve)monthLast.set(monthKey(p.date),p);const arr=[...monthLast.values()].sort((a,b)=>a.date.localeCompare(b.date));const out:number[]=[];for(let i=1;i<arr.length;i++)out.push(Math.log(arr[i].equity/arr[i-1].equity));return out;}
function sampleBlocks(pool:number[]){const out:number[]=[];while(out.length<MONTHS){const maxStart=Math.max(0,pool.length-BLOCK_MONTHS);const s=Math.floor(rng()*(maxStart+1));for(let j=0;j<BLOCK_MONTHS && out.length<MONTHS;j++)out.push(pool[s+j]);}return out;}
function shiftToTarget(sample:number[], targetCagr:number){const targetTotal=YEARS*Math.log1p(targetCagr);const active=sample.map((x,i)=>({x,i})).filter(v=>Math.abs(v.x)>1e-15);const current=sample.reduce((a,b)=>a+b,0);if(!active.length)return sample;const delta=(targetTotal-current)/active.length;return sample.map(x=>Math.abs(x)>1e-15?x+delta:0);}

type Sim = { terminal:number; totalWithdrawals:number; totalTax:number; depleted:boolean; minEquity:number; grossTerminalNoTaxNoWithdrawal:number; targetCagr:number };
function applyTaxAndWithdraw(logRets:number[], targetCagr:number, tax:boolean):Sim{
  let equity=1,totalWithdrawals=0,totalTax=0,minEquity=1,depleted=false;
  const losses:{amount:number; expiresAfterYear:number}[]=[];
  for(let y=0;y<YEARS;y++){
    const yearStart=equity;
    for(let m=0;m<12;m++){
      equity*=Math.exp(logRets[y*12+m]);
      minEquity=Math.min(minEquity,equity);
    }
    const netPnl=equity-yearStart;
    // Remove losses that expired before this tax year. A loss generated in year y is usable in y+1..y+3.
    for(let i=losses.length-1;i>=0;i--)if(losses[i].expiresAfterYear<y)losses.splice(i,1);
    if(tax){
      if(netPnl>0){
        let taxable=netPnl;
        for(const l of losses){const use=Math.min(taxable,l.amount);taxable-=use;l.amount-=use;if(taxable<=0)break;}
        for(let i=losses.length-1;i>=0;i--)if(losses[i].amount<=1e-15)losses.splice(i,1);
        const t=taxable*TAX_RATE;equity-=t;totalTax+=t;
      } else if(netPnl<0){
        losses.push({amount:-netPnl,expiresAfterYear:y+3});
      }
    }
    const w=Math.min(equity,WITHDRAWAL);equity-=w;totalWithdrawals+=w;
    minEquity=Math.min(minEquity,equity);
    if(equity<=1e-12){equity=0;depleted=true;break;}
  }
  return {terminal:equity,totalWithdrawals,totalTax,depleted,minEquity,grossTerminalNoTaxNoWithdrawal:Math.exp(logRets.reduce((a,b)=>a+b,0)),targetCagr};
}
function summary(xs:Sim[]){const terminals=xs.map(x=>x.terminal),taxes=xs.map(x=>x.totalTax),withdrawals=xs.map(x=>x.totalWithdrawals);return{
  terminal:{p05:q(terminals,.05),p10:q(terminals,.10),p25:q(terminals,.25),median:q(terminals,.50),p75:q(terminals,.75),p90:q(terminals,.90),p95:q(terminals,.95)},
  probabilityTerminalBelowInitial:terminals.filter(x=>x<1).length/xs.length,
  probabilityDepleted:xs.filter(x=>x.depleted).length/xs.length,
  probabilityFullWithdrawals:xs.filter(x=>x.totalWithdrawals>=WITHDRAWAL*YEARS-1e-9).length/xs.length,
  totalTax:{median:q(taxes,.5),p10:q(taxes,.1),p90:q(taxes,.9)},
  totalWithdrawals:{median:q(withdrawals,.5),p10:q(withdrawals,.1),p90:q(withdrawals,.9)},
};}
async function main(){
  const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};
  const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
  const bt=runBacktest({histories:market.histories,universeHistory:uf.history,config:PRODUCTION_STRATEGY});
  const pool=monthlyLogReturns(bt.equityCurve);
  const taxed:Sim[]=[], untaxed:Sim[]=[];
  for(let i=0;i<PATHS;i++){
    const target=sampleTargetCagr();
    const sampled=sampleBlocks(pool);
    const pathRets=shiftToTarget(sampled,target);
    taxed.push(applyTaxAndWithdraw(pathRets,target,true));
    untaxed.push(applyTaxAndWithdraw(pathRets,target,false));
  }
  const output={generatedAt:new Date().toISOString(),method:{paths:PATHS,years:YEARS,blockMonths:BLOCK_MONTHS,seed:SEED,taxRate:TAX_RATE,withdrawalPerYear:WITHDRAWAL,timing:"monthly returns; annual loss-netting/tax; then fixed withdrawal",historicalMonthlyPoolMonths:pool.length,forwardCagrPrior:cagrBins,tailCap:"The >=50% prior bin is simulated uniformly from 50% to 65%; means and extreme upper tails are therefore not interpreted."},validity:{trueOOS:false,subjectiveForwardPrior:true,historicalSequenceBootstrap:true,architectureHindsightRemains:true,taxApproximation:"Assumes monthly strategy P&L is realized and fully netted within each calendar year. Applies 20.315% tax to positive annual net realized gains after up to 3-year carried losses. Does not separately model intrayear withholding/refunds, dividends/US withholding, FX taxation, fees beyond the backtest, or NISA."},historical:{rawCagr:bt.stats.cagr,rawMaxDrawdown:bt.stats.maxDrawdown},taxed:summary(taxed),untaxed:summary(untaxed),comparisons:{medianTerminalTaxDrag:summary(untaxed).terminal.median-summary(taxed).terminal.median,medianTerminalRatioTaxedToUntaxed:summary(taxed).terminal.median/summary(untaxed).terminal.median}};
  const dir=path.join(process.cwd(),"data/research/tax-aware-10y");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
