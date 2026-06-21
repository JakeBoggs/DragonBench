import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
OBS="#121417"; PARCH="#F4EEE2"; EMBER="#D9482B"; GOLD="#E6A532"
EMERALD="#1F8A70"; TEAL="#3FB8AF"; INK="#23201B"; MUT="#8A8276"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK})

# ---- A) Sequencing cost (reading side) — REAL NHGRI figures ----
# Cited points from genome.gov "Cost of Sequencing a Human Genome".
yr=np.array([2003,2006,2015]); cost=np.array([50e6,14e6,1500.0])
fig,ax=plt.subplots(figsize=(7.4,5.0),dpi=200); fig.patch.set_facecolor(PARCH); ax.set_facecolor(PARCH)
ax.plot(yr,cost,"-o",color=EMERALD,lw=2.6,ms=9,zorder=4)
labs=["$50M (2003)","$14M (2006)","$1,500 (2015)"]
for x,y,l in zip(yr,cost,labs):
    ax.annotate(l,(x,y),xytext=(8,8),textcoords="offset points",fontsize=11,fontweight="bold",color=INK)
ax.set_yscale("log"); ax.set_ylim(500,2e8); ax.set_xlim(2002,2016.5)
ax.set_ylabel("Cost to sequence a human genome (US$)",fontsize=11)
ax.set_xlabel("Year",fontsize=11)
ax.set_title("Reading DNA fell ~30,000× in 12 years (NHGRI)",fontsize=13,fontweight="bold",pad=10)
ax.grid(True,which="major",color="#D8CFBC",lw=0.7); ax.set_axisbelow(True)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig("chart_seqcost.png",facecolor=PARCH,bbox_inches="tight"); plt.close(fig)

# ---- B) Schematic: how DragonBench supplies the 2nd axis ----
fig,ax=plt.subplots(figsize=(8.6,5.0),dpi=200); fig.patch.set_facecolor(PARCH); ax.set_facecolor(PARCH)
t=np.linspace(2015,2045,400)
def logi(t,mid,k=0.45): return 1/(1+np.exp(-k*(t-mid)))
write=logi(t,2034)
ax.plot(t,write,color=EMBER,lw=3,zorder=4,label="Genome-write capability  (external data)")
# design: solid up to today (low, schematic), dashed + fan after
today=2026
ts=t[t<=today]; td=t[t>=today]
design_s=0.18+0.012*(ts-2015)
ax.plot(ts,design_s,color=TEAL,lw=3,zorder=4,label="AI design capability  (DragonBench)")
d0=design_s[-1]
center=d0+ (td-today)*0.018
hi=d0+(td-today)*0.030; lo=d0+(td-today)*0.009
ax.fill_between(td,np.clip(lo,0,1),np.clip(hi,0,1),color=TEAL,alpha=0.15,zorder=1,lw=0)
ax.plot(td,np.clip(center,0,1),color=TEAL,lw=2,ls="--",zorder=3)
ax.scatter(ts[::3],design_s[::3],color=TEAL,s=18,zorder=5)
ax.text(2031,0.30,"your future runs\nfill this in",color=TEAL,fontsize=10,style="italic",ha="center")
# threshold
ax.axhline(0.8,color=MUT,ls=":",lw=1.6)
ax.text(2015.3,0.825,"design-grade threshold",color=MUT,fontsize=10)
ax.axvline(today,color=MUT,lw=1,alpha=0.5); ax.text(today+0.2,0.02,"today",color=MUT,fontsize=9,style="italic")
# gate: both cross
ax.text(2037.5,0.5,"Dragon =\nboth curves\nabove the line",color=INK,fontsize=11,fontweight="bold",ha="left",va="center")
ax.set_xlim(2015,2045); ax.set_ylim(0,1.02)
ax.set_ylabel("Capability (normalized)",fontsize=11); ax.set_xlabel("Year",fontsize=11)
ax.set_title("Schematic: DragonBench runs become the second forecast curve",fontsize=12.5,fontweight="bold",pad=10)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
ax.set_yticks([]); ax.grid(True,axis="x",color="#D8CFBC",lw=0.7); ax.set_axisbelow(True)
ax.legend(frameon=False,fontsize=10,loc="lower right")
fig.tight_layout(); fig.savefig("chart_plugin.png",facecolor=PARCH,bbox_inches="tight"); plt.close(fig)
print("extra charts written")
