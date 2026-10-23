"""Block diagrams: traditional vs SST data-center power chain, and ISOP-DAB arrangement."""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams.update({"font.family": "WenQuanYi Zen Hei", "axes.unicode_minus": False})
OUT = sys.argv[1]
BLUE, RED, GRAY = "#2f6db5", "#d1495b", "#555555"


def box(ax, x, y, w, h, text, color=BLUE, fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="white", ec=color, lw=1.6))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x1, y1, x2, y2, text=None, above=True, color="black"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4))
    if text:
        ax.text((x1 + x2) / 2, y1 + (0.18 if above else -0.18), text, ha="center",
                va="bottom" if above else "top", fontsize=9.5, color=GRAY)


# ------------------------------------------------ traditional vs SST chain
GAP = 1.25


def chain(ax, y, h, items, labels, fs=10.5):
    x = 0.15
    pos = []
    for t, w, c in items:
        box(ax, x, y, w, h, t, c, fs=fs)
        pos.append((x, w))
        x += w + GAP
    for (x1, w1), (x2, _), lab in zip(pos, pos[1:], labels):
        arrow(ax, x1 + w1 + 0.05, y + h / 2, x2 - 0.05, y + h / 2, lab)
    return pos


fig, ax = plt.subplots(figsize=(13, 4.8))
ax.set_xlim(0, 15.2); ax.set_ylim(0, 4.8); ax.axis("off")
ax.text(0.15, 4.5, "传统数据中心供电链路", fontsize=12.5, weight="bold", color=GRAY)
chain(ax, 3.15, 0.9,
      [("10 kV\n电网", 0.95, GRAY), ("工频变压器\n50 Hz", 1.3, GRAY), ("UPS\nAC/DC/AC", 1.3, GRAY),
       ("配电 PDU", 1.15, GRAY), ("服务器电源 PSU\nAC/DC + DC/DC", 1.95, GRAY), ("芯片\n负载", 0.95, GRAY)],
      ["10 kV AC", "400 V AC", "400 V AC", "230 V AC", "54/12 V DC"])
ax.text(0.15, 2.3, "SST + 800 V 直流供电（AIDC 新架构）", fontsize=12.5, weight="bold", color=RED)
pos = chain(ax, 0.75, 1.05,
            [("10 kV\n电网", 0.95, RED), ("① 中压 AC/DC\n级联 H 桥 / MMC", 1.8, BLUE),
             ("② 隔离 DC/DC\nDAB / CLLC 模块\n(ISOP)", 1.8, BLUE), ("③ 机柜内 DC/DC\n800 V → 54/12 V", 1.95, BLUE),
             ("芯片\n负载", 0.95, RED)],
            ["10 kV AC", "中压直流", "800 V DC", "54/12 V DC"])
x_sst0, x_sst1 = pos[1][0], pos[2][0] + pos[2][1]
ax.plot([x_sst0, x_sst1], [0.62, 0.62], color=BLUE, lw=1.2)
ax.text((x_sst0 + x_sst1) / 2, 0.22, "固态变压器 SST = ① + ②：用高频隔离代替工频变压器，减少变换级数、直接输出直流",
        ha="center", fontsize=10, color=BLUE)
fig.savefig(f"{OUT}/sst-aidc-architecture.png", dpi=160, bbox_inches="tight", facecolor="white")
plt.close(fig)

# ------------------------------------------------ ISOP DAB modules
fig, ax = plt.subplots(figsize=(8, 5.2))
ax.set_xlim(0, 8); ax.set_ylim(-0.3, 5.2); ax.axis("off")
N = 3
ys = [3.7, 2.2, 0.2]
for k, y in enumerate(ys):
    name = f"DAB 模块 {k + 1}" if k < 2 else "DAB 模块 N"
    box(ax, 3.0, y, 2.0, 1.0, name + "\n高频变压器隔离", BLUE, fs=10.5)
    # input terminals (left): series
    ax.plot([2.2, 3.0], [y + 0.8, y + 0.8], color="k", lw=1.4)
    ax.plot([2.2, 3.0], [y + 0.2, y + 0.2], color="k", lw=1.4)
    ax.text(2.6, y + 0.5, f"$V_{{in,{k + 1 if k < 2 else 'N'}}}$", ha="center", va="center", fontsize=10)
    # output terminals (right): parallel
    ax.plot([5.0, 6.2], [y + 0.8, y + 0.8], color="k", lw=1.4)
    ax.plot([5.0, 6.1], [y + 0.2, y + 0.2], color="k", lw=1.4)          # hop over the + bus
    th = np.linspace(np.pi, 0, 30)
    ax.plot(6.2 + 0.1 * np.cos(th), y + 0.2 + 0.1 * np.sin(th), color="k", lw=1.4)
    ax.plot([6.3, 6.6], [y + 0.2, y + 0.2], color="k", lw=1.4)
    ax.plot([6.2], [y + 0.8], "o", color=RED, ms=4); ax.plot([6.6], [y + 0.2], "o", color=RED, ms=4)
# series links on input side
ax.plot([2.2, 2.2], [ys[0] + 0.2, ys[1] + 0.8], color="k", lw=1.4)
ax.plot([2.2, 2.2], [ys[1] + 0.2, ys[1] - 0.25], color="k", lw=1.4)
ax.plot([2.2, 2.2], [ys[2] + 0.8, ys[2] + 1.25], color="k", lw=1.4)
ax.text(2.2, ys[2] + 1.55, r"$\vdots$", ha="center", va="center", fontsize=16)
ax.plot([1.0, 2.2], [ys[0] + 0.8, ys[0] + 0.8], color="k", lw=1.4)
ax.plot([1.0, 2.2], [ys[2] + 0.2, ys[2] + 0.2], color="k", lw=1.4)
ax.text(0.95, ys[0] + 0.8, "+", ha="right", va="center", fontsize=13)
ax.text(0.95, ys[2] + 0.2, "$-$", ha="right", va="center", fontsize=13)
ax.text(0.55, 2.5, "中压直流\n（如 10 kV 整流后）\n输入串联\n各模块分压", ha="center", va="center", fontsize=10.5)
# parallel bus on output side
ax.plot([6.2, 6.2], [ys[2] + 0.8, ys[0] + 0.8], color=RED, lw=1.8)
ax.plot([6.6, 6.6], [ys[2] + 0.2, ys[0] + 0.2], color=RED, lw=1.8)
ax.text(7.0, 2.5, "800 V\n直流母线\n输出并联\n各模块分流", ha="left", va="center", fontsize=10.5, color=RED)
ax.text(4.0, 5.0, "ISOP（输入串联、输出并联）：用低压器件搭出中压变换器", ha="center", fontsize=11.5, weight="bold")
ax.text(4.0, -0.25, "关键问题：输入均压 $V_{in,1}=V_{in,2}=\\cdots$，输出均流，单模块故障时冗余切除",
        ha="center", fontsize=10, color=GRAY)
fig.savefig(f"{OUT}/sst-isop-dab.png", dpi=160, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("ok")
