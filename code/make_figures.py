"""Figures that depend only on the study design (no study data)."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OI = {"blue":"#0072B2","orange":"#E69F00","green":"#009E73","verm":"#D55E00","grey":"#666666"}
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9})

def box(ax,x,y,w,h,text,fc="#F2F2F2",ec="#444444",fs=8.5,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.08",fc=fc,ec=ec,lw=1))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,fontweight="bold" if bold else "normal",wrap=True)

def arrow(ax,x1,y1,x2,y2):
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle="-|>",color="#444444",lw=1))

def fig_design(path):
    fig,ax=plt.subplots(figsize=(7.4,5.2)); ax.set_xlim(0,10); ax.set_ylim(0,7.4); ax.axis("off")
    box(ax,3.0,6.5,4.0,0.75,"MedQuAD: Cancer.gov, NIDDK, NHLBI\none question per source document",fc="#DCEBF7")
    box(ax,0.4,5.2,3.6,0.85,"12 development questions\n(rubric calibration, pilot)",fc="#FBEFD0")
    box(ax,6.0,5.2,3.6,0.85,"100 held-out test questions\n(34 / 33 / 33 by source)",fc="#DCEBF7")
    arrow(ax,4.4,6.5,2.4,6.05); arrow(ax,5.6,6.5,7.8,6.05)
    box(ax,0.4,3.7,4.3,1.0,"Set A: ordinary answers\nLlama 3 8B or Qwen2.5 7B writes each answer;\nanswers split into atomic claims",fc="#E3F3EC")
    box(ax,5.3,3.7,4.3,1.0,"Set B: controlled pairs\nsupported paraphrase + minimally edited claim\n(contradiction, addition, certainty or scope)",fc="#FBE3D6")
    arrow(ax,7.8,5.2,2.55,4.7); arrow(ax,7.8,5.2,7.45,4.7)
    box(ax,2.2,2.3,5.6,0.95,"Blinded human reference\ntwo independent reviewers, third adjudicates;\nlabels: supported / unsupported / unassessable",fc="#F2F2F2")
    arrow(ax,2.55,3.7,4.0,3.25); arrow(ax,7.45,3.7,6.0,3.25)
    box(ax,0.4,0.55,5.0,1.2,"Judges run on frozen inputs\n2 models x 3 prompts (P1-P3) x 3 seeds\nreference condition: P1, seed 17\n(+ greedy-decoding reference arm)",fc="#DCEBF7")
    box(ax,6.0,0.55,3.6,1.2,"Endpoints (paired bootstrap\nover questions)\ndetection; prompt and seed\ndisagreement; failure patterns",fc="#FFFFFF")
    arrow(ax,5.0,2.3,3.0,1.75); arrow(ax,5.4,1.15,6.0,1.15)
    fig.tight_layout(); fig.savefig(path,dpi=300); plt.close(fig)

def wilson_half(p,n,z=1.96):
    return z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)*100

def fig_precision(path):
    n=np.arange(10,201); fig,ax=plt.subplots(figsize=(5.6,3.7))
    for p,c,ls in [(0.7,OI["verm"],"-"),(0.8,OI["blue"],"-"),(0.9,OI["green"],"-")]:
        ax.plot(n,wilson_half(p,n),color=c,ls=ls,lw=1.8,label=f"true sensitivity {p:.1f}")
    for k in (30,100):
        v=wilson_half(0.8,k); ax.plot([k],[v],"o",color=OI["blue"],ms=5)
        ax.annotate(f"n={k}: ±{v:.1f} pts",(k,v),textcoords="offset points",xytext=(8,6),fontsize=8)
    ax.set_xlabel("Number of adjudicated unsupported claims (independent)")
    ax.set_ylabel("Approximate 95% half-width (percentage points)")
    ax.set_ylim(0,25); ax.grid(alpha=.3); ax.legend(frameon=False)
    for s in ("top","right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(path,dpi=300); plt.close(fig)

if __name__=="__main__":
    fig_design("fig_design.png"); fig_precision("fig_precision.png"); print("ok")
