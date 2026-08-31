import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'data/research/fixed60-falsification-core/result.json'
OUT=ROOT/'data/research/fixed60-forward40-density'; OUT.mkdir(parents=True,exist_ok=True)
N=100; YEARS=10; SPY=252; BLOCK=63; WITHDRAW=0.075; SEED=20260831; STEP=21; TARGET=0.40
with INPUT.open() as f: result=json.load(f)
curve=result['baseline']['afterTaxCurve']; eq=np.array([float(p['equity']) for p in curve]); dates=[p['date'] for p in curve]
r=np.diff(np.log(eq)); hist_mean=float(r.mean()); target_mean=float(np.log1p(TARGET)/SPY); adj=r-hist_mean+target_mean
rng=np.random.default_rng(SEED); ns=YEARS*SPY; paths=np.empty((N,ns+1)); paths[:,0]=1
mx=len(adj)-BLOCK
for i in range(N):
    s=[]
    while len(s)<ns:
        k=int(rng.integers(0,mx+1)); s.extend(adj[k:k+BLOCK])
    w=1.0
    for t,x in enumerate(np.asarray(s[:ns]),1):
        w*=float(np.exp(x))
        if t%SPY==0: w-=WITHDRAW
        w=max(w,1e-6); paths[i,t]=w
idx=np.unique(np.r_[np.arange(0,ns+1,STEP),ns]); times=idx/SPY; sp=paths[:,idx]
ylog=np.linspace(-1,3,260); yedges=10**ylog; yc=.5*(ylog[:-1]+ylog[1:]); h=np.zeros((len(times),len(yc)))
for j in range(len(times)): h[j],_=np.histogram(np.log10(np.clip(sp[:,j],.1,1000)),bins=ylog)
sm=gaussian_filter(h,sigma=(1.4,2.2),mode='nearest'); sm=sm/sm.max() if sm.max()>0 else sm
p05,p50,p95=[np.quantile(sp,q,axis=0) for q in (.05,.5,.95)]
fig,ax=plt.subplots(figsize=(10,10.5),dpi=180); mesh=ax.pcolormesh(times,yedges[:-1],sm.T,shading='auto',cmap='viridis',vmin=0,vmax=1)
ax.plot(times,p95,linewidth=1.5,label='95th percentile'); ax.plot(times,p50,linewidth=2.3,label='50th percentile'); ax.plot(times,p05,linewidth=1.5,label='5th percentile')
ax.set_yscale('log'); ax.set_xlim(0,YEARS); ax.set_ylim(.1,1000); ax.set_xticks(np.arange(0,YEARS+1)); ax.set_xlabel('Years'); ax.set_ylabel('Wealth multiple (log scale)'); ax.grid(True,which='major',axis='both',alpha=.25)
ax.set_title('100-Path Density Gradient — Forward Target-Calibrated (40% CAGR)\nInitial investment = 1, annual withdrawal = 0.075',pad=10)
c=fig.colorbar(mesh,ax=ax,pad=.045); c.set_label('Relative path density'); c.set_ticks([0,.25,.5,.75,1])
fig.text(.5,.015,f'Source: Fixed60 after-tax curve {dates[0]} to {dates[-1]} | drift recalibrated to 40% pre-withdrawal CAGR | 63-session moving-block bootstrap | seed {SEED}',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.035,1,1)); png=OUT/'fixed60-forward40-100-path-density-20260831.png'; fig.savefig(png,bbox_inches='tight'); plt.close(fig)
meta={'generatedFrom':{'curveStart':dates[0],'curveEnd':dates[-1],'historicalAfterTaxStats':result['baseline']['afterTax'],'taxApproximation':result['validity']['taxApproximation']},'calibration':{'targetForwardCagr':TARGET,'scope':'return process before withdrawals','formula':'r_adj = r_hist - mean(r_hist) + ln(1.40)/252','historicalDailyLogMean':hist_mean,'targetDailyLogMean':target_mean,'note':'Scenario calibration, not a calibrated probability forecast.'},'simulation':{'paths':N,'years':YEARS,'sessionsPerYear':SPY,'blockSessions':BLOCK,'initialInvestment':1.0,'annualWithdrawal':WITHDRAW,'withdrawalTiming':'end of each simulated 252-session year','seed':SEED},'terminalWealth':{'p05':float(np.quantile(paths[:,-1],.05)),'median':float(np.quantile(paths[:,-1],.5)),'p95':float(np.quantile(paths[:,-1],.95)),'min':float(paths[:,-1].min()),'max':float(paths[:,-1].max()),'shareBelow1':float(np.mean(paths[:,-1]<1))}}
with (OUT/'metadata.json').open('w') as f: json.dump(meta,f,indent=2)
print(json.dumps(meta,indent=2)); print(png)
