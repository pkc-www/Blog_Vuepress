<script setup lang="ts">
import { computed, ref } from "vue";

type Mode = "bounds" | "loss";
const mode = ref<Mode>("bounds");

// Mode 1: Bounds (Lec 12 Sec 6-7)
const pdBounds = ref(700); // MW in [250, 1200]
const useLimits = ref(true);

// Mode 2: Transmission loss (Lec 12 Sec 8-9)
const pdLoss = ref(350); // MW in [150, 500]
const bLoss = ref(0.001); // B22 in [0, 0.0025]

const clamp = (v: number, lo: number, hi: number): number => Math.min(hi, Math.max(lo, v));

const boundsSim = computed(() => {
  const PD = pdBounds.value;
  const p1Min = useLimits.value ? 150 : 0;
  const p1Max = useLimits.value ? 300 : PD;
  const p2Min = useLimits.value ? 100 : 0;
  const p2Max = useLimits.value ? 900 : PD;

  const cost1 = (p: number) => 9000 + 450 * p + 0.1 * p * p;
  const cost2 = (p: number) => 25000 + 430 * p + 0.03 * p * p;
  const ic1Fn = (p: number) => 450 + 0.2 * p;
  const ic2Fn = (p: number) => 430 + 0.06 * p;

  // Bisection lambda iteration
  let lo = 400;
  let hi = 700;
  for (let i = 0; i < 60; i++) {
    const mid = 0.5 * (lo + hi);
    const p1 = clamp((mid - 450) / 0.2, p1Min, p1Max);
    const p2 = clamp((mid - 430) / 0.06, p2Min, p2Max);
    if (p1 + p2 < PD) lo = mid;
    else hi = mid;
  }
  const lam = 0.5 * (lo + hi);
  const p1 = clamp((lam - 450) / 0.2, p1Min, p1Max);
  const p2 = PD - p1;
  const ic1 = ic1Fn(p1);
  const ic2 = ic2Fn(p2);
  const ct = cost1(p1) + cost2(p2);

  // Also compute unconstrained optimum for comparison
  const p1Unc = clamp((0.06 * PD - 20) / 0.26, 0, PD);
  const ctUnc = cost1(p1Unc) + cost2(PD - p1Unc);

  // Feasible P1 interval for given PD
  const fLo = Math.max(p1Min, PD - p2Max);
  const fHi = Math.min(p1Max, PD - p2Min);

  // Scan P1 in [0, min(PD, 450)] for cost & IC plots
  const p1Span = Math.min(PD, 450);
  const scanP1: number[] = [];
  const scanCT: number[] = [];
  const scanIC1: number[] = [];
  const scanIC2: number[] = [];
  const steps = 90;
  for (let i = 0; i <= steps; i++) {
    const x = (p1Span * i) / steps;
    scanP1.push(x);
    scanCT.push(cost1(x) + cost2(PD - x));
    scanIC1.push(ic1Fn(x));
    scanIC2.push(ic2Fn(PD - x));
  }

  let kktTag = "两机均在内部 (IC₁ = IC₂ = λ)";
  if (useLimits.value && Math.abs(p1 - p1Min) < 0.05 && ic1 > lam + 0.05) {
    kktTag = "机组 1 顶下限 (IC₁ > λ = IC₂)";
  } else if (useLimits.value && Math.abs(p2 - p2Max) < 0.05 && ic2 < lam - 0.05) {
    kktTag = "机组 2 顶上限 (IC₂ < λ = IC₁)";
  } else if (useLimits.value && Math.abs(p1 - p1Max) < 0.05 && ic1 < lam - 0.05) {
    kktTag = "机组 1 顶上限 (IC₁ < λ = IC₂)";
  }

  return { p1, p2, lam, ic1, ic2, ct, p1Unc, ctUnc, fLo, fHi, p1Span, scanP1, scanCT, scanIC1, scanIC2, kktTag };
});

const lossSim = computed(() => {
  const PD = pdLoss.value;
  const B = bLoss.value;

  const icFn = (p: number) => 0.07 * p + 41;
  const cFn = (p: number) => 41 * p + 0.035 * p * p; // variable cost integral of IC

  // Bisection on lambda
  // P1(lam) = (lam - 41)/0.07
  // P2(lam) = ((1 + 100*B)*lam - 41) / (0.07 + 2*B*lam)
  let lo = 41;
  let hi = 120;
  for (let i = 0; i < 65; i++) {
    const mid = 0.5 * (lo + hi);
    const p1 = (mid - 41) / 0.07;
    const p2 = ((1 + 100 * B) * mid - 41) / (0.07 + 2 * B * mid);
    const pl = B * (p2 - 50) * (p2 - 50);
    if (p1 + p2 - pl < PD) lo = mid;
    else hi = mid;
  }
  const lam = 0.5 * (lo + hi);
  const p1 = (lam - 41) / 0.07;
  const p2 = ((1 + 100 * B) * lam - 41) / (0.07 + 2 * B * lam);
  const pl = B * (p2 - 50) * (p2 - 50);
  const ic1 = icFn(p1);
  const ic2 = icFn(p2);
  const dPlDp2 = 2 * B * (p2 - 50);
  const alpha2 = 1 / Math.max(0.05, 1 - dPlDp2);
  const delivIC2 = alpha2 * ic2;
  const ct = cFn(p1) + cFn(p2);

  // Scan P2 in [50, min(260, PD)] where P1 = PD + PL(P2) - P2
  const p2Lo = 50;
  const p2Hi = Math.min(260, PD - 20);
  const scanP2: number[] = [];
  const scanCT: number[] = [];
  const scanIC1: number[] = [];
  const scanIC2: number[] = [];
  const scanAIC2: number[] = [];
  const steps = 84;
  for (let i = 0; i <= steps; i++) {
    const x2 = p2Lo + ((p2Hi - p2Lo) * i) / steps;
    const lx = B * (x2 - 50) * (x2 - 50);
    const x1 = PD + lx - x2;
    const dL = 2 * B * (x2 - 50);
    if (dL >= 0.92) continue;
    scanP2.push(x2);
    scanCT.push(cFn(x1) + cFn(x2));
    scanIC1.push(icFn(x1));
    scanIC2.push(icFn(x2));
    scanAIC2.push(icFn(x2) / (1 - dL));
  }

  return { p1, p2, pl, lam, ic1, ic2, alpha2, delivIC2, ct, p2Lo, p2Hi, scanP2, scanCT, scanIC1, scanIC2, scanAIC2 };
});

// Unified plotting helpers (Left: Cost C_T, Right: IC curves)
const W = 320;
const H = 212;
const pL = 44;
const pR = 14;
const pT = 16;
const pB = 26;

const plotData = computed(() => {
  if (mode.value === "bounds") {
    const s = boundsSim.value;
    const xLo = 0;
    const xHi = Math.max(10, s.p1Span);
    const cMin = Math.min(...s.scanCT);
    const cMax = Math.max(...s.scanCT);
    const cPad = Math.max(200, (cMax - cMin) * 0.14);

    const icAll = [...s.scanIC1, ...s.scanIC2];
    const iMin = Math.min(...icAll) - 5;
    const iMax = Math.max(...icAll) + 5;

    const mx = (x: number) => pL + ((x - xLo) / (xHi - xLo)) * (W - pL - pR);
    const myC = (c: number) => pT + ((cMax + cPad - c) / (cMax - cMin + 2 * cPad)) * (H - pT - pB);
    const myI = (v: number) => pT + ((iMax - v) / (iMax - iMin)) * (H - pT - pB);

    const path = (xs: number[], ys: number[], yFn: (v: number) => number) =>
      xs.map((x, i) => `${i === 0 ? "M" : "L"}${mx(x).toFixed(1)},${yFn(ys[i]).toFixed(1)}`).join(" ");

    return {
      costPath: path(s.scanP1, s.scanCT, myC),
      icAPath: path(s.scanP1, s.scanIC1, myI),
      icBPath: path(s.scanP1, s.scanIC2, myI),
      icCPath: "",
      optX: mx(s.p1),
      optCostY: myC(s.ct),
      optLamY: myI(s.lam),
      feasX1: useLimits.value ? mx(Math.max(xLo, s.fLo)) : pL,
      feasX2: useLimits.value ? mx(Math.min(xHi, s.fHi)) : W - pR,
      xAxisLbl: "P_G1 (MW)",
      xMinLbl: "0",
      xMaxLbl: `${xHi.toFixed(0)}`,
      cMinLbl: `${(cMin / 1000).toFixed(0)}k`,
      cMaxLbl: `${(cMax / 1000).toFixed(0)}k`,
      iMinLbl: `${iMin.toFixed(0)}`,
      iMaxLbl: `${iMax.toFixed(0)}`,
    };
  }

  const s = lossSim.value;
  const xLo = s.p2Lo;
  const xHi = Math.max(xLo + 10, s.p2Hi);
  const cMin = Math.min(...s.scanCT);
  const cMax = Math.max(...s.scanCT);
  const cPad = Math.max(50, (cMax - cMin) * 0.14);

  const icAll = [...s.scanIC1, ...s.scanIC2, ...s.scanAIC2];
  const iMin = Math.min(...icAll) - 2;
  const iMax = Math.min(115, Math.max(...icAll) + 2);

  const mx = (x: number) => pL + ((x - xLo) / (xHi - xLo)) * (W - pL - pR);
  const myC = (c: number) => pT + ((cMax + cPad - c) / (cMax - cMin + 2 * cPad)) * (H - pT - pB);
  const myI = (v: number) => pT + ((iMax - Math.min(iMax, v)) / (iMax - iMin)) * (H - pT - pB);

  const path = (xs: number[], ys: number[], yFn: (v: number) => number) =>
    xs.map((x, i) => `${i === 0 ? "M" : "L"}${mx(x).toFixed(1)},${yFn(ys[i]).toFixed(1)}`).join(" ");

  return {
    costPath: path(s.scanP2, s.scanCT, myC),
    icAPath: path(s.scanP2, s.scanIC1, myI),
    icBPath: path(s.scanP2, s.scanIC2, myI),
    icCPath: path(s.scanP2, s.scanAIC2, myI),
    optX: mx(s.p2),
    optCostY: myC(s.ct),
    optLamY: myI(s.lam),
    feasX1: pL,
    feasX2: W - pR,
    xAxisLbl: "P_G2 (MW)",
    xMinLbl: `${xLo}`,
    xMaxLbl: `${xHi.toFixed(0)}`,
    cMinLbl: `${(cMin / 1000).toFixed(1)}k`,
    cMaxLbl: `${(cMax / 1000).toFixed(1)}k`,
    iMinLbl: `${iMin.toFixed(0)}`,
    iMaxLbl: `${iMax.toFixed(0)}`,
  };
});
</script>

<template>
  <div class="ps-lab">
    <div class="ps-head">
      <div>
        <span class="ps-badge">交互实验 · INTERACTIVE LAB</span>
        <h4 class="ps-title">经济调度实验室：等微增率、KKT 出力边界与网损惩罚因子</h4>
      </div>
      <span class="ps-status is-ok">
        {{ mode === "bounds" ? boundsSim.kktTag : `α₂ = ${lossSim.alpha2.toFixed(3)} · α₂IC₂ = IC₁ = λ` }}
      </span>
    </div>

    <div class="ps-presets">
      <button type="button" class="ps-chip" :class="{ 'is-active': mode === 'bounds' }" @click="mode = 'bounds'">
        模式 1：两机出力上下限 (KKT)
      </button>
      <button type="button" class="ps-chip" :class="{ 'is-active': mode === 'loss' }" @click="mode = 'loss'">
        模式 2：计及网损与惩罚因子 αᵢ
      </button>
      <template v-if="mode === 'bounds'">
        <button type="button" class="ps-chip" @click="pdBounds = 700; useLimits = false">课件 700 MW (无约束)</button>
        <button type="button" class="ps-chip" @click="pdBounds = 700; useLimits = true">700 MW (机组1顶下限)</button>
        <button type="button" class="ps-chip" @click="pdBounds = 1020; useLimits = true">1020 MW (双机自由调节)</button>
        <button type="button" class="ps-chip" @click="pdBounds = 1140; useLimits = true">1140 MW (机组2顶上限)</button>
      </template>
      <template v-else>
        <button type="button" class="ps-chip" @click="pdLoss = 350; bLoss = 0">无网损 (B₂₂=0, 均分 175 MW)</button>
        <button type="button" class="ps-chip" @click="pdLoss = 350; bLoss = 0.001">课件含网损例 (B₂₂=0.001)</button>
        <button type="button" class="ps-chip" @click="pdLoss = 420; bLoss = 0.0015">重载高网损 (机组2大幅让出)</button>
      </template>
    </div>

    <div class="ps-controls">
      <template v-if="mode === 'bounds'">
        <label class="ps-slider">
          <span class="ps-slider-row">
            <span>系统总负荷 P<sub>D</sub>（转折点 983.3 / 1070 MW）</span>
            <strong>{{ pdBounds }} MW</strong>
          </span>
          <input v-model.number="pdBounds" type="range" min="250" max="1200" step="10" />
        </label>
        <label class="ps-check">
          <input v-model="useLimits" type="checkbox" />
          <span>启用出力上下限（150 ≤ P<sub>G1</sub> ≤ 300，100 ≤ P<sub>G2</sub> ≤ 900 MW）</span>
        </label>
      </template>

      <template v-else>
        <label class="ps-slider">
          <span class="ps-slider-row">
            <span>系统总负荷 P<sub>D</sub></span>
            <strong>{{ pdLoss }} MW</strong>
          </span>
          <input v-model.number="pdLoss" type="range" min="180" max="480" step="10" />
        </label>
        <label class="ps-slider">
          <span class="ps-slider-row">
            <span>线路网损系数 B<sub>22</sub>（P<sub>L</sub> = B<sub>22</sub>(P<sub>G2</sub> − 50)²）</span>
            <strong>{{ bLoss.toFixed(4) }}</strong>
          </span>
          <input v-model.number="bLoss" type="range" min="0" max="0.0022" step="0.0001" />
        </label>
      </template>
    </div>

    <div class="ps-grid">
      <!-- Total Cost curve -->
      <div class="ps-panel">
        <div class="ps-panel-label">总小时发电成本 C<sub>T</sub>（浅绿为可行域，蓝点为最优解）</div>
        <svg :viewBox="`0 0 ${W} ${H}`" class="ps-svg">
          <rect
            v-if="mode === 'bounds' && useLimits"
            :x="plotData.feasX1"
            :y="pT"
            :width="Math.max(2, plotData.feasX2 - plotData.feasX1)"
            :height="H - pT - pB"
            class="svg-feas"
          />
          <line :x1="pL" :y1="pT" :x2="pL" :y2="H - pB" class="svg-axis" />
          <line :x1="pL" :y1="H - pB" :x2="W - pR" :y2="H - pB" class="svg-axis" />
          <path :d="plotData.costPath" fill="none" class="svg-cost" />
          <line :x1="plotData.optX" :y1="pT" :x2="plotData.optX" :y2="H - pB" class="svg-guide" />
          <circle :cx="plotData.optX" :cy="plotData.optCostY" r="5" class="svg-dot" />
          <text :x="pL - 5" :y="pT + 6" class="svg-tick" text-anchor="end">{{ plotData.cMaxLbl }}</text>
          <text :x="pL - 5" :y="H - pB + 3" class="svg-tick" text-anchor="end">{{ plotData.cMinLbl }}</text>
          <text :x="pL" :y="H - 9" class="svg-tick">{{ plotData.xMinLbl }}</text>
          <text :x="W - pR" :y="H - 9" class="svg-tick" text-anchor="end">{{ plotData.xAxisLbl }} ({{ plotData.xMaxLbl }})</text>
        </svg>
      </div>

      <!-- IC curves -->
      <div class="ps-panel">
        <div class="ps-panel-label">
          {{ mode === "bounds" ? "微增率 IC₁ (蓝) vs. IC₂ (红) 与系统边际成本 λ" : "IC₁ (蓝)、本机 IC₂ (灰虚) 与修正送达微增率 α₂IC₂ (红)" }}
        </div>
        <svg :viewBox="`0 0 ${W} ${H}`" class="ps-svg">
          <line :x1="pL" :y1="pT" :x2="pL" :y2="H - pB" class="svg-axis" />
          <line :x1="pL" :y1="H - pB" :x2="W - pR" :y2="H - pB" class="svg-axis" />
          <line :x1="pL" :y1="plotData.optLamY" :x2="W - pR" :y2="plotData.optLamY" class="svg-lam" />
          <path :d="plotData.icAPath" fill="none" class="svg-ic1" />
          <path :d="plotData.icBPath" fill="none" :class="mode === 'bounds' ? 'svg-ic2' : 'svg-ic2-raw'" />
          <path v-if="mode === 'loss'" :d="plotData.icCPath" fill="none" class="svg-ic2" />
          <circle :cx="plotData.optX" :cy="plotData.optLamY" r="5" class="svg-dot" />
          <text :x="pL - 5" :y="pT + 6" class="svg-tick" text-anchor="end">{{ plotData.iMaxLbl }}</text>
          <text :x="pL - 5" :y="H - pB + 3" class="svg-tick" text-anchor="end">{{ plotData.iMinLbl }}</text>
          <text :x="W - pR - 2" :y="Math.max(24, plotData.optLamY - 5)" class="svg-lam-lbl" text-anchor="end">
            λ = {{ (mode === "bounds" ? boundsSim.lam : lossSim.lam).toFixed(2) }}
          </text>
          <text :x="W - pR" :y="H - 9" class="svg-tick" text-anchor="end">{{ plotData.xAxisLbl }}</text>
        </svg>
      </div>
    </div>

    <div v-if="mode === 'bounds'" class="ps-metrics">
      <div class="ps-metric">
        <span>最优分配 P<sub>G1</sub>* / P<sub>G2</sub>*</span>
        <strong>{{ boundsSim.p1.toFixed(1) }} / {{ boundsSim.p2.toFixed(1) }} MW</strong>
      </div>
      <div class="ps-metric">
        <span>系统边际成本 λ*</span>
        <strong>{{ boundsSim.lam.toFixed(2) }} 元/MWh</strong>
      </div>
      <div class="ps-metric">
        <span>各机微增率 IC<sub>1</sub> / IC<sub>2</sub></span>
        <strong>{{ boundsSim.ic1.toFixed(1) }} / {{ boundsSim.ic2.toFixed(1) }} 元/MWh</strong>
      </div>
      <div class="ps-metric">
        <span>最小小时成本 C<sub>T</sub>*</span>
        <strong>{{ boundsSim.ct.toFixed(0) }} 元/h</strong>
      </div>
    </div>

    <div v-else class="ps-metrics">
      <div class="ps-metric">
        <span>最优出力 P<sub>G1</sub>* / P<sub>G2</sub>*</span>
        <strong>{{ lossSim.p1.toFixed(2) }} / {{ lossSim.p2.toFixed(2) }} MW</strong>
      </div>
      <div class="ps-metric">
        <span>线路网损 P<sub>L</sub>*</span>
        <strong>{{ lossSim.pl.toFixed(2) }} MW</strong>
      </div>
      <div class="ps-metric">
        <span>本机 IC<sub>1</sub> / IC<sub>2</sub></span>
        <strong>{{ lossSim.ic1.toFixed(2) }} / {{ lossSim.ic2.toFixed(2) }} 元/MWh</strong>
      </div>
      <div class="ps-metric">
        <span>惩罚因子 α<sub>2</sub> &amp; α<sub>2</sub>IC<sub>2</sub></span>
        <strong>{{ lossSim.alpha2.toFixed(3) }} → {{ lossSim.delivIC2.toFixed(2) }}</strong>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ps-lab {
  margin: 1.4rem 0;
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg-alt);
  font-size: 0.9rem;
  line-height: 1.5;
}

.ps-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--vp-c-divider);
}

.ps-badge {
  display: inline-block;
  color: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.ps-title {
  margin: 0.15rem 0 0 !important;
  color: var(--ink);
  font-size: 1.02rem;
  font-weight: 700;
}

.ps-status {
  padding: 0.2rem 0.62rem;
  border: 1px solid #1e7a56;
  border-radius: var(--r, 2px);
  background: rgb(30 122 86 / 12%);
  color: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 0.75rem;
  font-weight: 600;
}

.ps-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-bottom: 0.75rem;
}

.ps-chip {
  padding: 0.24rem 0.58rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
  color: var(--vp-c-text);
  font-size: 0.79rem;
  cursor: pointer;

  &.is-active,
  &:hover {
    border-color: var(--vp-c-accent);
    background: var(--vp-c-accent-soft);
    color: var(--vp-c-accent);
    font-weight: 600;
  }
}

.ps-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem 1.1rem;
  align-items: center;
  margin-bottom: 0.85rem;
}

.ps-slider {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.ps-slider-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.81rem;

  strong {
    color: var(--vp-c-accent);
    font-family: var(--vp-font-mono);
    font-variant-numeric: tabular-nums;
  }
}

.ps-check {
  display: inline-flex;
  gap: 0.45rem;
  align-items: center;
  font-size: 0.82rem;
  cursor: pointer;
}

input[type="range"] {
  width: 100%;
  accent-color: var(--vp-c-accent);
  cursor: pointer;
}

.ps-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.ps-panel {
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.ps-panel-label {
  margin-bottom: 0.28rem;
  color: var(--vp-c-text-mute);
  font-size: 0.75rem;
  font-weight: 600;
}

.ps-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-feas {
  fill: #1e7a56;
  opacity: 0.1;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
}

.svg-guide {
  stroke: var(--vp-c-border);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-cost,
.svg-ic1 {
  stroke: var(--vp-c-accent);
  stroke-width: 2.2;
}

.svg-ic2 {
  stroke: #c83e37;
  stroke-width: 2.2;
}

.svg-ic2-raw {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-lam {
  stroke: #1e7a56;
  stroke-width: 1.3;
  stroke-dasharray: 4 3;
}

.svg-lam-lbl {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-dot {
  fill: var(--vp-c-accent);
  stroke: var(--vp-c-bg);
  stroke-width: 1.8;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
}

.ps-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.48rem;
}

.ps-metric {
  padding: 0.42rem 0.56rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);

  span {
    display: block;
    color: var(--vp-c-text-mute);
    font-size: 0.7rem;
  }

  strong {
    display: block;
    margin-top: 0.14rem;
    color: var(--ink);
    font-family: var(--vp-font-mono);
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .ps-controls,
  .ps-grid {
    grid-template-columns: 1fr;
  }

  .ps-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
