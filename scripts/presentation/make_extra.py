import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
OBS="#121417"; PARCH="#F4EEE2"; EMBER="#D9482B"; GOLD="#E6A532"
EMERALD="#1F8A70"; TEAL="#2E9E8C"; INK="#23201B"; MUT="#8A8276"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK})

# ---- A) Sequencing cost (reading) — REAL, updated to 2024 ----
# NHGRI series + Illumina NovaSeq X (~$200, 2024).
yr=np.array([2003,2006,2015,2024]); cost=np.array([50e6,14e6,1500.0,200.0])
fig,ax=plt.subplots(figsize=(7.4,5.0),dpi=200); fig.patch.set_facecolor(PARCH); ax.set_facecolor(PARCH)
ax.plot(yr,cost,"-o",color=EMERALD,lw=2.6,ms=9,zorder=4)
for x,y,l in zip(yr,cost,["$50M (2003)","$14M (2006)","$1,500 (2015)","$200 (2024)"]):
    ax.annotate(l,(x,y),xytext=(7,8),textcoords="offset points",fontsize=11,fontweight="bold",color=INK)
ax.set_yscale("log"); ax.set_ylim(80,2e8); ax.set_xlim(2002,2026)
ax.set_ylabel("Cost to sequence a human genome (US$)",fontsize=11); ax.set_xlabel("Year",fontsize=11)
ax.set_title(r"Reading DNA: \$50M $\rightarrow$ \$200 in two decades (NHGRI; Illumina 2024)",fontsize=12.5,fontweight="bold",pad=10)
ax.grid(True,which="major",color="#D8CFBC",lw=0.7); ax.set_axisbelow(True)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig("chart_seqcost.png",facecolor=PARCH,bbox_inches="tight"); plt.close(fig)

# ---- B) TWO CAPABILITIES vs the dragon target ----
write=[(2003,5386,"φX174"),(2008,582970,"M. genitalium"),(2010,1077947,"syn1.0"),
       (2019,4.0e6,"E. coli Syn61"),(2023,1.2e7,"Sc2.0 yeast")]
design=[(2023,600,"RFdiffusion"),(2024,690,"ESM3 (esmGFP)"),(2025,5.8e5,"Evo 2 (in silico)")]
TARGET=1.6e9
wx=np.array([w[0] for w in write]); wy=np.log10([w[1] for w in write])
b,a=np.polyfit(wx,wy,1); cross=(np.log10(TARGET)-a)/b
fig,ax=plt.subplots(figsize=(10.4,5.3),dpi=200); fig.patch.set_facecolor(PARCH); ax.set_facecolor(PARCH)
# write series + extrapolation
ax.plot(wx,10**wy,"-o",color=EMBER,lw=2.6,ms=8,zorder=5,label="Physically written & booted (validated)")
xe=np.linspace(2023,cross,50); ax.plot(xe,10**(a+b*xe),color=EMBER,lw=2,ls="--",zorder=4)
ax.plot([cross],[TARGET],"o",color=EMBER,ms=10,zorder=6)
ax.annotate("~%.0f"%cross,(cross,TARGET),xytext=(4,10),textcoords="offset points",fontsize=12,fontweight="bold",color=EMBER)
# design series (in silico)
dx=np.array([d[0] for d in design]); dy=np.array([d[1] for d in design])
ax.plot(dx,dy,"-o",color=TEAL,lw=2.6,ms=8,zorder=5,label="AI-designed in silico (untested in cells)")
doff={"RFdiffusion":(-6,-15,"right"),"ESM3 (esmGFP)":(8,6,"left"),"Evo 2 (in silico)":(8,10,"left")}
for (x,v,l) in design:
    ox,oy,ha=doff[l]
    ax.annotate(l,(x,v),xytext=(ox,oy),textcoords="offset points",fontsize=9,color="#1d6b5f",ha=ha)
for (x,v,l) in write:
    ax.annotate(l,(x,v),xytext=(0,-15),textcoords="offset points",fontsize=8.3,color="#7a5a3a",ha="center")
ax.axhline(TARGET,color=EMERALD,lw=1.8,ls=":",zorder=3)
ax.text(2002.4,TARGET*1.6,"Dragon genome — 1.6 Gb",color=EMERALD,fontsize=10.5,fontweight="bold")
ax.set_yscale("log"); ax.set_ylim(1e2,1e10); ax.set_xlim(2002,2040)
ax.set_ylabel("Sequence length handled (bp)",fontsize=11); ax.set_xlabel("Year",fontsize=11)
ax.set_title("Two capabilities a dragon needs — both far below 1.6 Gb today",fontsize=13,fontweight="bold",pad=10)
ax.grid(True,which="major",color="#D8CFBC",lw=0.7); ax.set_axisbelow(True)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
ax.legend(frameon=False,fontsize=9.5,loc="lower right")
fig.tight_layout(); fig.savefig("chart_twocap.png",facecolor=PARCH,bbox_inches="tight"); plt.close(fig)
print("design in-silico SOTA 2025: 0.58 Mb ; write/boot 2023: 12 Mb ; target 1600 Mb ; write-curve crossing ~%.0f"%cross)
print("charts written")
