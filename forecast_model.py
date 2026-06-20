import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
rng=np.random.default_rng(7)

OBS="#121417"; PARCH="#F4EEE2"; EMBER="#D9482B"; GOLD="#E6A532"
EMERALD="#1F8A70"; TEAL="#3FB8AF"; INK="#23201B"; MUT="#8A8276"

# ---------------------------------------------------------------
# MODEL
# Each skill is forecast to reach "design-grade reliability" (a threshold
# stricter than benchmark-best: reliable on realistic, generalizing inputs).
# Crossing-year priors below are ANCHORED to cited milestones but the
# spread/median for un-crossed skills are explicit modeling assumptions.
#   T_dragon = max_i(T_i) + L_integration
# ---------------------------------------------------------------
N=200000
# (name, prior_mean, prior_sd, status)  -- normal prior on crossing year
skills = {
 "ProteinFold":  (2021, 1.0, "crossed (AF2, CASP14 2020)"),
 "GeneParse":    (2020, 1.0, "crossed (SpliceAI 2019)"),
 "TFBind":       (2024, 2.0, "near (DeepBind AUROC~0.92 since 2015; affinity-grade rising)"),
 "RNAFold":      (2026, 2.0, "in progress (cross-family F1 ~0.65 and rising)"),
 "PromoterExpr": (2031, 3.0, "bottleneck (seq->expr corr ~0.85, design-grade early 2030s)"),
}
T = {k: rng.normal(m,s,N) for k,(m,s,_) in skills.items()}
Tmax = np.maximum.reduce(list(T.values()))
# Integration lag: components-solved -> verified end-to-end design pipeline.
# Grounded loosely in synthetic-biology precedent (method maturity -> integrated
# synthetic genome historically ~5-15 yr). Lognormal, median ~7.
L = rng.lognormal(mean=np.log(7), sigma=0.35, size=N)
Tdragon = Tmax + L

med = np.median(Tdragon)
lo,hi = np.percentile(Tdragon,[10,90])
# which skill is the binding max, how often
which = np.array(list(T.keys()))[np.argmax(np.vstack([T[k] for k in T]),axis=0)]
binding = {k: float((which==k).mean()) for k in T}
print("MEDIAN", round(med,1), "80%CI", round(lo,1), round(hi,1))
print("binding-constraint share:", {k:round(v,2) for k,v in binding.items()})
print("median integration lag", round(np.median(L),1))

# ===============================================================
# CHART A: skill track record + crossing forecast (light)
# ===============================================================
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK})
fig,ax=plt.subplots(figsize=(10.2,5.0),dpi=200); fig.patch.set_facecolor(PARCH); ax.set_facecolor(PARCH)
order=["ProteinFold","GeneParse","TFBind","RNAFold","PromoterExpr"]
colmap={"ProteinFold":EMERALD,"GeneParse":EMERALD,"TFBind":GOLD,"RNAFold":GOLD,"PromoterExpr":EMBER}
# cited real milestones (year, label)
miles={
 "ProteinFold":[(2018,"AF1"),(2020,"AF2")],
 "GeneParse":[(2019,"SpliceAI")],
 "TFBind":[(2015,"DeepBind")],
 "RNAFold":[(2019,"SPOT-RNA"),(2022,"UFold")],
 "PromoterExpr":[(2021,"Enformer"),(2023,"Borzoi")],
}
for i,k in enumerate(order):
    y=len(order)-1-i
    m,s,_=skills[k]
    # forecast crossing band (10-90)
    clo,chi=np.percentile(T[k],[10,90]); cmed=np.median(T[k])
    ax.plot([clo,chi],[y,y],color=colmap[k],lw=9,alpha=0.22,solid_capstyle="round",zorder=1)
    ax.plot(cmed,y,"D",color=colmap[k],ms=9,zorder=4)
    for (yr,lab) in miles[k]:
        ax.plot(yr,y,"o",color=INK,ms=6,zorder=5)
        ax.annotate(lab,(yr,y),xytext=(0,8),textcoords="offset points",
                    ha="center",fontsize=8.5,color="#4A453C")
ax.axvline(2026,color=MUT,ls=":",lw=1.2)
ax.text(2026.1,4.55,"today",color=MUT,fontsize=9,style="italic")
ax.set_yticks(range(len(order)))
ax.set_yticklabels(order[::-1],fontsize=11)
ax.set_xlim(2013,2037); ax.set_ylim(-0.6,4.9)
ax.set_xlabel("Year",fontsize=11)
ax.set_title("Component skills: cited milestones (●) and forecast design-grade crossing (◆ median, band = 10–90%)",
             fontsize=11.5,fontweight="bold",pad=10)
for sp in["top","right","left"]: ax.spines[sp].set_visible(False)
ax.xaxis.grid(True,color="#D8CFBC",lw=0.7); ax.set_axisbelow(True)
ax.tick_params(left=False)
fig.tight_layout(); fig.savefig("chart_skills.png",facecolor=PARCH,bbox_inches="tight"); plt.close(fig)

# ===============================================================
# CHART B: Monte Carlo distribution of dragon-readiness (dark)
# ===============================================================
plt.rcParams.update({"text.color":PARCH})
fig,ax=plt.subplots(figsize=(10.2,5.0),dpi=200); fig.patch.set_facecolor(OBS); ax.set_facecolor(OBS)
bins=np.arange(2028,2052,0.5)
ax.hist(Tdragon,bins=bins,color=EMBER,alpha=0.55,edgecolor=OBS)
ax.axvline(med,color=GOLD,lw=2.5)
ax.axvspan(lo,hi,color=GOLD,alpha=0.10)
ax.axvline(lo,color=GOLD,ls="--",lw=1.2); ax.axvline(hi,color=GOLD,ls="--",lw=1.2)
ymax=ax.get_ylim()[1]
ax.text(med,ymax*0.96,"median\n%d"%round(med),color=GOLD,fontsize=13,fontweight="bold",ha="center",va="top")
ax.text(lo,ymax*0.55,"%d"%round(lo),color=GOLD,fontsize=11,ha="right")
ax.text(hi,ymax*0.55,"%d"%round(hi),color=GOLD,fontsize=11,ha="left")
ax.text(0.985,0.80,"80%% interval\n%d – %d"%(round(lo),round(hi)),transform=ax.transAxes,
        color=PARCH,fontsize=12,ha="right",va="top")
ax.set_xlabel("Projected year of dragon-grade design capability",fontsize=11,color=PARCH)
ax.set_ylabel("Monte Carlo draws",fontsize=11,color=PARCH)
ax.set_title("Forecast = max(component crossings) + integration lag   (200k simulations)",
             fontsize=12,fontweight="bold",color=PARCH,pad=10)
for sp in["top","right"]: ax.spines[sp].set_visible(False)
for sp in["left","bottom"]: ax.spines[sp].set_color("#3A3F45")
ax.tick_params(colors=PARCH)
ax.grid(True,axis="y",color="#2A2E33",lw=0.7); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig("chart_forecast.png",facecolor=OBS,bbox_inches="tight"); plt.close(fig)
print("charts written")
