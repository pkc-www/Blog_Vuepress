"""Generate blog figures for the power-electronics series (Buck + DAB)."""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams.update({
    "font.family": "WenQuanYi Zen Hei",
    "axes.unicode_minus": False,
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
})
OUT = sys.argv[1]
C1, C2, C3 = "#2f6db5", "#d1495b", "#3a9d5d"

# ---------------- Buck CCM ----------------
Vin, D, fs, L, Io = 48, 0.25, 100e3, 22e-6, 5
Ts = 1 / fs
Vo = D * Vin
dI = (Vin - Vo) * D * Ts / L
t = np.linspace(0, 3 * Ts, 3000)
ph = (t / Ts) % 1
on = ph < D
vsw = np.where(on, Vin, 0)
iL = np.where(on, Io - dI / 2 + dI * ph / D, Io + dI / 2 - dI * (ph - D) / (1 - D))
fig, ax = plt.subplots(2, 1, figsize=(7, 4.2), sharex=True)
ax[0].plot(t * 1e6, vsw, C1)
ax[0].axhline(Vo, color=C2, ls="--", lw=1)
ax[0].text(t[-1] * 1e6 * 0.99, Vo + 2, f"平均值 = D·Vin = {Vo:.0f} V", color=C2, ha="right")
ax[0].set_ylabel("开关节点电压 [V]")
ax[1].plot(t * 1e6, iL, C1)
ax[1].axhline(Io, color=C2, ls="--", lw=1)
ax[1].set_ylabel("电感电流 [A]")
ax[1].set_xlabel("t [μs]")
ax[0].set_title(f"Buck 变换器 CCM 稳态波形（Vin={Vin} V, D={D}, ΔiL={dI:.2f} A）")
fig.savefig(f"{OUT}/buck-ccm-waveform.png")
plt.close(fig)

# ---------------- DAB SPS helpers ----------------
V1, n, fs, L = 800, 2, 50e3, 40e-6
Ts = 1 / fs
Th = Ts / 2


def sps_wave(d, M, npts=4000):
    """Ideal SPS waveforms over one period, V2 held constant (V2' = M*V1)."""
    V2p = M * V1
    i0 = -V1 / (4 * fs * L) * (1 - M * (1 - 2 * d))
    t = np.linspace(0, Ts, npts, endpoint=False)
    ph = (t / Ts) % 1
    vp = np.where(ph < 0.5, V1, -V1)
    vs = np.where(((ph - d / 2) % 1) < 0.5, V2p, -V2p)
    i = np.zeros_like(t)
    dt = t[1] - t[0]
    i[0] = i0
    for k in range(len(t) - 1):
        i[k + 1] = i[k] + (vp[k] - vs[k]) / L * dt
    return t, vp, vs, i


# --- SPS waveform, M = 1, phi = 30 deg ---
d = 30 / 180
t, vp, vs, i = sps_wave(d, 1.0)
fig, ax = plt.subplots(2, 1, figsize=(7.5, 4.8), sharex=True)
ax[0].plot(t * 1e6, vp, C1, label="$v_p$（原边桥）")
ax[0].plot(t * 1e6, vs, C2, ls="--", label="$n v_s$（副边桥，折算到原边）")
ax[0].annotate("", xy=(d * Th * 1e6, 950), xytext=(0, 950),
               arrowprops=dict(arrowstyle="<->", color="k"))
ax[0].text(d * Th * 1e6 / 2, 1000, "φ", ha="center")
ax[0].set_ylim(-1100, 1150)
ax[0].set_ylabel("电压 [V]")
ax[0].legend(loc="center left", bbox_to_anchor=(0.14, 0.5), fontsize=9)
ax[1].plot(t * 1e6, i, C3)
ax[1].set_ylabel("$i_L$ [A]")
ax[1].set_xlabel("t [μs]")
for tt, lab in [(0, "$i_0$"), (d * Th, "$i_1$")]:
    k = int(round(tt / Ts * len(t)))
    ax[1].plot(t[k] * 1e6, i[k], "ko", ms=4)
    ax[1].text(t[k] * 1e6 + 0.3, i[k] + (4 if i[k] > 0 else 3), lab)
ax[0].set_title("DAB 单移相（SPS）稳态波形：V1=800 V，n=2，V2=400 V，φ=30°")
fig.savefig(f"{OUT}/dab-sps-waveform.png")
plt.close(fig)

# --- backflow illustration ---
fig, ax = plt.subplots(1, 1, figsize=(7.5, 3.2))
t, vp, vs, i = sps_wave(d, 1.0)
p = vp * i
ax.plot(t * 1e6, p / 1e3, C1, label="瞬时功率 $p = v_p i_L$")
ax.fill_between(t * 1e6, p / 1e3, 0, where=p < 0, color=C2, alpha=0.35, label="回流功率（回到原边电源）")
ax.axhline(np.mean(p) / 1e3, color="k", ls="--", lw=1, label=f"平均功率 {np.mean(p)/1e3:.1f} kW")
ax.set_xlabel("t [μs]")
ax.set_ylabel("p [kW]")
ax.set_title("同一工况下原边桥的瞬时功率：红色部分就是回流功率")
ax.legend(fontsize=9, loc="lower right")
fig.savefig(f"{OUT}/dab-backflow.png")
plt.close(fig)

# --- power vs phase ---
phis = np.linspace(-180, 180, 721)
dd = phis / 180
P = n * V1 * 400 * dd * (1 - np.abs(dd)) / (2 * fs * L)
pts = np.arange(-180, 181, 15)
Pn = []
for ph_ in pts:
    _, vp_, vs_, i_ = sps_wave(ph_ / 180, 1.0, 6000)
    Pn.append(np.mean(vp_ * i_))
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.plot(phis, P / 1e3, C1, lw=2, label="公式 $P=\\frac{nV_1V_2}{2f_sL}d(1-|d|)$")
ax.plot(pts, np.array(Pn) / 1e3, "o", color=C2, ms=5, label="数值积分")
ax.axvspan(90, 180, color="0.85")
ax.axvspan(-180, -90, color="0.85")
ax.text(135, -30, "一般不用\n(电流大、功率反而下降)", ha="center", fontsize=9)
ax.set_xlabel("移相角 φ [度]（正：原边→副边；负：副边→原边）")
ax.set_ylabel("P [kW]")
ax.set_title("DAB 传输功率随移相角变化：天然双向")
ax.legend(fontsize=9, loc="upper left")
fig.savefig(f"{OUT}/dab-power-vs-phase.png")
plt.close(fig)

# --- ZVS region ---
dg = np.linspace(0, 0.5, 400)
Mg = np.linspace(0.3, 2.0, 400)
DD, MM = np.meshgrid(dg, Mg)
pri_ok = 1 - MM * (1 - 2 * DD) >= 0      # i0 <= 0
sec_ok = MM + 2 * DD - 1 >= 0            # i1 >= 0
fig, ax = plt.subplots(figsize=(6.4, 4.4))
ax.contourf(DD * 180, MM, (pri_ok & sec_ok).astype(float), levels=[-0.5, 0.5, 1.5],
            colors=["#f3c4c9", "#cfe8d6"])
ax.plot(dg * 180, 1 / (1 - 2 * dg + 1e-9), C2, lw=1.5)
ax.plot(dg * 180, 1 - 2 * dg, C1, lw=1.5)
ax.set_ylim(0.3, 2.0)
ax.set_xlim(0, 90)
ax.text(8, 1.8, "原边失去 ZVS\n$M > 1/(1-2d)$", color=C2, fontsize=10)
ax.text(5, 0.45, "副边失去 ZVS\n$M < 1-2d$", color=C1, fontsize=10)
ax.text(55, 1.1, "全部 ZVS", fontsize=12)
ax.axhline(1, color="k", ls=":", lw=1)
ax.set_xlabel("移相角 φ [度]")
ax.set_ylabel("电压增益 $M = nV_2/V_1$")
ax.set_title("SPS 调制的软开关（ZVS）范围")
fig.savefig(f"{OUT}/dab-zvs-region.png")
plt.close(fig)

# --- startup transient (same model as dab_sps.m) ---
Rs, Cc = 0.05, 100e-6
d = 30 / 180
P_th = n * V1 * 400 * d * (1 - d) / (2 * fs * L)
R = 400 ** 2 / P_th
dt = Ts / 720
N = int(10e-3 / dt)
iL = np.zeros(N)
vo = np.zeros(N)
sq = lambda x: 1.0 if (x % 1) < 0.5 else -1.0
for k in range(N - 1):
    tm = (k + 0.5) * dt
    sp = sq(tm / Ts)
    ss = sq(tm / Ts - d / 2)
    di1 = (sp * V1 - n * ss * vo[k] - Rs * iL[k]) / L
    dv1 = (n * ss * iL[k] - vo[k] / R) / Cc
    ip, vop = iL[k] + dt * di1, vo[k] + dt * dv1
    di2 = (sp * V1 - n * ss * vop - Rs * ip) / L
    dv2 = (n * ss * ip - vop / R) / Cc
    iL[k + 1] = iL[k] + dt * (di1 + di2) / 2
    vo[k + 1] = vo[k] + dt * (dv1 + dv2) / 2
tt = np.arange(N) * dt
fig, ax = plt.subplots(2, 1, figsize=(7.5, 4.6), sharex=True)
ax[0].plot(tt * 1e3, vo, C1)
ax[0].set_ylabel("$v_o$ [V]")
ax[0].set_title(f"开环启动：φ=30°，R={R:.1f} Ω，C=100 μF（稳态 vo≈{vo[-2000:].mean():.0f} V）")
ax[1].plot(tt * 1e3, iL, C3, lw=0.4)
ax[1].set_ylabel("$i_L$ [A]")
ax[1].set_xlabel("t [ms]")
ax[1].text(0.3, iL.max() * 0.85, "启动时 vo≈0，电感电流很大且上下不对称（含直流偏置）\n直流分量只能靠 Rs 慢慢衰减 → 实际工程需要软启动", fontsize=9)
fig.savefig(f"{OUT}/dab-startup.png")
plt.close(fig)
print("vo_ss", vo[-2000:].mean(), "R", R)
