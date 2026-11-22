<script setup lang="ts">
import { computed, ref } from "vue";

const busType = ref<"PQ" | "PV">("PQ");
const pLoad = ref(4.0); // Bus 2 active load (P2_sp = -pLoad), default 4.0 matches Lec 9
const qLoad = ref(0.0); // Bus 2 reactive load (Q2_sp = -qLoad)
const rxRatio = ref(0.0); // R/X ratio (0 = lossless Lec 9 case, up to 1.0 distribution line)
const xLine = 0.1;
const bShunt = 0.1; // each end j0.1

const applyPreset = (type: "PQ" | "PV", p: number, q: number, rx: number): void => {
  busType.value = type;
  pLoad.value = p;
  qLoad.value = q;
  rxRatio.value = rx;
};

const sim = computed(() => {
  const X = xLine;
  const R = rxRatio.value * X;
  const z2 = R * R + X * X;
  const g12 = R / z2;
  const b12 = -X / z2;
  const G21 = -g12;
  const B21 = -b12;
  const G22 = g12;
  const B22 = b12 + bShunt; // negative for inductive line

  const Psp = -pLoad.value;
  const Qsp = -qLoad.value;
  const isPV = busType.value === "PV";

  const calcPQ = (U: number, d: number) => {
    const c = Math.cos(d);
    const s = Math.sin(d);
    const P = U * U * G22 + U * (G21 * c + B21 * s);
    const Q = -U * U * B22 + U * (G21 * s - B21 * c);
    return { P, Q };
  };

  // --- Full Polar Newton-Raphson ---
  const nrRes: number[] = [];
  let uNR = 1.0;
  let dNR = 0.0;
  let nrConv = false;
  const maxIter = 30;
  const tol = 1e-11;

  for (let k = 0; k <= maxIter; k++) {
    const { P, Q } = calcPQ(uNR, dNR);
    const dP = Psp - P;
    const dQ = isPV ? 0 : Qsp - Q;
    const err = Math.max(Math.abs(dP), Math.abs(dQ));
    nrRes.push(Math.max(err, 1e-14));
    if (err < tol) {
      nrConv = true;
      break;
    }
    if (k === maxIter || !Number.isFinite(err) || err > 1e5) break;

    if (isPV) {
      const H = Q + uNR * uNR * B22;
      if (Math.abs(H) < 1e-10) break;
      dNR += -dP / H;
    } else {
      const H = Q + uNR * uNR * B22;
      const N = -P - uNR * uNR * G22;
      const M = -P + uNR * uNR * G22;
      const L = -Q + uNR * uNR * B22;
      const det = H * L - N * M;
      if (Math.abs(det) < 1e-10) break;
      const dd = (-dP * L + dQ * N) / det;
      const eta = (-H * dQ + M * dP) / det;
      dNR += dd;
      uNR = Math.max(0.05, uNR * (1 + eta));
    }
  }

  // --- Fast Decoupled (PQ) ---
  const pqRes: number[] = [];
  let uPQ = 1.0;
  let dPQ = 0.0;
  let pqConv = false;

  for (let k = 0; k <= maxIter; k++) {
    const { P, Q } = calcPQ(uPQ, dPQ);
    const dP = Psp - P;
    const dQ = isPV ? 0 : Qsp - Q;
    const err = Math.max(Math.abs(dP), Math.abs(dQ));
    pqRes.push(Math.max(err, 1e-14));
    if (err < tol) {
      pqConv = true;
      break;
    }
    if (k === maxIter || !Number.isFinite(err) || err > 1e5) break;

    // Step 1: P-delta
    dPQ += -dP / (uPQ * B22);
    // Step 2: Q-U (with updated angle)
    if (!isPV) {
      const { Q: Qnew } = calcPQ(uPQ, dPQ);
      const dQnew = Qsp - Qnew;
      uPQ = Math.max(0.05, uPQ - dQnew / (uPQ * B22));
    }
  }

  // Slack & reactive results from converged N-R (or PQ fallback)
  const solved = nrConv || pqConv;
  const uSol = nrConv ? uNR : uPQ;
  const dSol = nrConv ? dNR : dPQ;
  const dDeg = (dSol * 180) / Math.PI;
  const { Q: Q2calc } = calcPQ(uSol, dSol);
  // Bus 1 injection: Y11 = y12 + j*bShunt = G22 + j*B22, Y12 = G21 + j*B21, delta12 = -dSol
  const P1 = G22 + uSol * (G21 * Math.cos(-dSol) + B21 * Math.sin(-dSol));
  const Q1 = -B22 + uSol * (G21 * Math.sin(-dSol) - B21 * Math.cos(-dSol));

  // P-U nose curve for current R/X and qLoad (PQ mode)
  // Equation: -B22*U^2 + U*(G21*sin d - B21*cos d) = -qLoad
  // Let A = -B22 (>0), B(d) = G21*sin d - B21*cos d (<0 for normal d), C = qLoad
  // A U^2 + B U + C = 0
  const noseUpper: { p: number; u: number }[] = [];
  const noseLower: { p: number; u: number }[] = [];
  const A = -B22;
  let pMaxNose = 0;
  for (let deg = 0; deg >= -115; deg -= 1) {
    const d = (deg * Math.PI) / 180;
    const B = G21 * Math.sin(d) - B21 * Math.cos(d);
    const disc = B * B - 4 * A * qLoad.value;
    if (disc < 0) continue;
    const uHi = (-B + Math.sqrt(disc)) / (2 * A);
    const uLo = (-B - Math.sqrt(disc)) / (2 * A);
    if (uHi > 0) {
      const pHi = -(uHi * uHi * G22 + uHi * (G21 * Math.cos(d) + B21 * Math.sin(d)));
      if (pHi >= -0.05) {
        noseUpper.push({ p: Math.max(0, pHi), u: uHi });
        if (pHi > pMaxNose) pMaxNose = pHi;
      }
    }
    if (uLo > 0) {
      const pLo = -(uLo * uLo * G22 + uLo * (G21 * Math.cos(d) + B21 * Math.sin(d)));
      if (pLo >= -0.05) {
        noseLower.push({ p: Math.max(0, pLo), u: uLo });
      }
    }
  }
  const noseCurve = [...noseUpper, ...noseLower.reverse()];

  return {
    nrRes,
    pqRes,
    nrConv,
    pqConv,
    nrIters: nrRes.length - 1,
    pqIters: pqRes.length - 1,
    solved,
    uSol,
    dDeg,
    P1,
    Q1,
    Q2calc,
    noseCurve,
    pMaxNose,
  };
});

// Convergence SVG
const CW = 330;
const CH = 210;
const cx = (iter: number): number => 42 + (iter / 30) * (CW - 54);
const cy = (res: number): number => {
  const lg = Math.max(-12, Math.min(2, Math.log10(Math.max(res, 1e-14))));
  return 16 + ((2 - lg) / 14) * (CH - 42);
};

const nrPath = computed(() =>
  sim.value.nrRes.map((r, i) => `${i === 0 ? "M" : "L"}${cx(i).toFixed(1)},${cy(r).toFixed(1)}`).join(" ")
);
const pqPath = computed(() =>
  sim.value.pqRes.map((r, i) => `${i === 0 ? "M" : "L"}${cx(i).toFixed(1)},${cy(r).toFixed(1)}`).join(" ")
);

// Nose curve SVG
const NW = 310;
const NH = 210;
const pSpan = computed(() => Math.max(6, Math.ceil(sim.value.pMaxNose * 1.15)));
const nx = (p: number): number => 40 + (Math.min(pSpan.value, Math.max(0, p)) / pSpan.value) * (NW - 54);
const ny = (u: number): number => NH - 26 - (Math.min(1.25, Math.max(0, u)) / 1.25) * (NH - 42);

const nosePath = computed(() =>
  sim.value.noseCurve.map((pt, i) => `${i === 0 ? "M" : "L"}${nx(pt.p).toFixed(1)},${ny(pt.u).toFixed(1)}`).join(" ")
);
</script>

<template>
  <div class="ps-lab">
    <div class="ps-head">
      <div>
        <span class="ps-badge">交互实验 · INTERACTIVE LAB</span>
        <h4 class="ps-title">两节点潮流计算：极坐标牛顿法 (N-R) vs. PQ 分解法实时收敛对比</h4>
      </div>
      <span class="ps-status" :class="sim.solved ? 'is-ok' : 'is-bad'">
        {{ sim.solved ? `已收敛 · U₂ = ${sim.uSol.toFixed(4)} pu` : "潮流无解 / 发散 (越过鼻点)" }}
      </span>
    </div>

    <div class="ps-presets">
      <button type="button" class="ps-chip" :class="{ 'is-active': busType === 'PQ' }" @click="busType = 'PQ'">
        节点 2 为 PQ
      </button>
      <button type="button" class="ps-chip" :class="{ 'is-active': busType === 'PV' }" @click="busType = 'PV'">
        节点 2 转为 PV (U₂=1)
      </button>
      <button type="button" class="ps-chip" @click="applyPreset('PQ', 4.0, 0.0, 0.0)">课件原例 (R/X=0, P=4)</button>
      <button type="button" class="ps-chip" @click="applyPreset('PQ', 4.0, 0.0, 0.65)">高 R/X 配网 (PQ 变慢/发散!)</button>
      <button type="button" class="ps-chip" @click="applyPreset('PQ', 4.95, 0.0, 0.0)">逼近电压崩溃鼻点</button>
      <button type="button" class="ps-chip" @click="applyPreset('PV', 4.0, 0.0, 0.0)">课件 PV 改型 (δ₂=−23.58°)</button>
    </div>

    <div class="ps-controls">
      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>净有功负荷 P<sub>L2</sub> = −P<sub>2</sub><sup>sp</sup></span>
          <strong>{{ pLoad.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="pLoad" type="range" min="0.5" max="6.0" step="0.05" />
      </label>

      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>净无功负荷 Q<sub>L2</sub> = −Q<sub>2</sub><sup>sp</sup></span>
          <strong>{{ qLoad.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="qLoad" type="range" min="-1.5" max="2.5" step="0.05" :disabled="busType === 'PV'" />
      </label>

      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>线路阻抗比 R / X（X = 0.1）</span>
          <strong>{{ rxRatio.toFixed(2) }}</strong>
        </span>
        <input v-model.number="rxRatio" type="range" min="0" max="1.0" step="0.05" />
      </label>
    </div>

    <div class="ps-grid">
      <!-- Convergence -->
      <div class="ps-panel">
        <div class="ps-panel-label">残差收敛曲线 log₁₀ max(|ΔP|, |ΔQ|)（实线 N-R 二阶 / 虚线 PQ 线性）</div>
        <svg :viewBox="`0 0 ${CW} ${CH}`" class="ps-svg">
          <line x1="42" :y1="cy(1e-11)" :x2="CW - 12" :y2="cy(1e-11)" class="svg-tol" />
          <line x1="42" y1="14" x2="42" :y2="CH - 26" class="svg-axis" />
          <line x1="42" :y1="CH - 26" :x2="CW - 12" :y2="CH - 26" class="svg-axis" />
          <path :d="pqPath" fill="none" class="svg-pq" />
          <path :d="nrPath" fill="none" class="svg-nr" />
          <text v-for="e in [0, -4, -8, -12]" :key="e" x="36" :y="cy(Math.pow(10, e)) + 3" class="svg-tick" text-anchor="end">
            10{{ e === 0 ? "⁰" : e === -4 ? "⁻⁴" : e === -8 ? "⁻⁸" : "⁻¹²" }}
          </text>
          <text v-for="it in [0, 10, 20, 30]" :key="'i' + it" :x="cx(it)" :y="CH - 9" class="svg-tick" text-anchor="middle">
            {{ it }}
          </text>
          <text :x="CW - 14" y="26" class="svg-lbl-nr" text-anchor="end">
            N-R: {{ sim.nrConv ? sim.nrIters + " 次" : "未收敛" }}
          </text>
          <text :x="CW - 14" y="40" class="svg-lbl-pq" text-anchor="end">
            PQ: {{ sim.pqConv ? sim.pqIters + " 次" : "未收敛" }}
          </text>
        </svg>
      </div>

      <!-- P-U Nose Curve -->
      <div class="ps-panel">
        <div class="ps-panel-label">节点 2 的 P–U 鼻形曲线（上限 P<sub>max</sub> ≈ {{ sim.pMaxNose.toFixed(2) }} pu）</div>
        <svg :viewBox="`0 0 ${NW} ${NH}`" class="ps-svg">
          <line x1="40" :y1="ny(1.0)" :x2="NW - 14" :y2="ny(1.0)" class="svg-ref" />
          <line x1="40" y1="16" x2="40" :y2="NH - 26" class="svg-axis" />
          <line x1="40" :y1="NH - 26" :x2="NW - 14" :y2="NH - 26" class="svg-axis" />
          <path :d="nosePath" fill="none" class="svg-nose" />
          <circle v-if="sim.solved" :cx="nx(pLoad)" :cy="ny(sim.uSol)" r="5" class="svg-dot" />
          <text x="34" :y="ny(1.0) + 3" class="svg-tick" text-anchor="end">1.0</text>
          <text x="34" :y="ny(0.5) + 3" class="svg-tick" text-anchor="end">0.5</text>
          <text x="34" :y="ny(0) + 3" class="svg-tick" text-anchor="end">0</text>
          <text :x="NW - 14" :y="NH - 9" class="svg-tick" text-anchor="end">P_L (max {{ pSpan }})</text>
        </svg>
      </div>
    </div>

    <div class="ps-metrics">
      <div class="ps-metric">
        <span>收敛电压 U<sub>2</sub> ∠ δ<sub>2</sub></span>
        <strong>{{ sim.solved ? `${sim.uSol.toFixed(4)} ∠ ${sim.dDeg.toFixed(2)}°` : "无解" }}</strong>
      </div>
      <div class="ps-metric">
        <span>N-R / PQ 迭代步数</span>
        <strong>{{ sim.nrConv ? sim.nrIters : "×" }} / {{ sim.pqConv ? sim.pqIters : "×" }} 步</strong>
      </div>
      <div class="ps-metric">
        <span>平衡节点注入 P<sub>1</sub> + jQ<sub>1</sub></span>
        <strong>{{ sim.solved ? `${sim.P1.toFixed(3)} ${sim.Q1 >= 0 ? "+" : "−"} j${Math.abs(sim.Q1).toFixed(3)}` : "—" }}</strong>
      </div>
      <div class="ps-metric">
        <span>{{ busType === "PV" ? "节点 2 所需无功注入 Q₂" : "当前极限输送有功 P_max" }}</span>
        <strong>{{ busType === "PV" ? (sim.solved ? sim.Q2calc.toFixed(4) + " pu" : "—") : sim.pMaxNose.toFixed(3) + " pu" }}</strong>
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
  border-radius: var(--r, 2px);
  font-family: var(--vp-font-mono);
  font-size: 0.76rem;
  font-weight: 600;

  &.is-ok {
    border: 1px solid #1e7a56;
    background: rgb(30 122 86 / 12%);
    color: #1e7a56;
  }

  &.is-bad {
    border: 1px solid #c83e37;
    background: rgb(200 62 55 / 14%);
    color: #c83e37;
  }
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem 1rem;
  margin-bottom: 0.85rem;
}

.ps-slider {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
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

input[type="range"] {
  width: 100%;
  accent-color: var(--vp-c-accent);
  cursor: pointer;

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.ps-grid {
  display: grid;
  grid-template-columns: 1.08fr 1fr;
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

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
}

.svg-tol {
  stroke: #1e7a56;
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-ref {
  stroke: var(--vp-c-border);
  stroke-width: 1;
  stroke-dasharray: 4 3;
}

.svg-nr {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
}

.svg-pq {
  stroke: #c83e37;
  stroke-width: 2;
  stroke-dasharray: 5 3;
}

.svg-nose {
  stroke: #1e7a56;
  stroke-width: 2.2;
}

.svg-dot {
  fill: var(--vp-c-accent);
  stroke: var(--vp-c-bg);
  stroke-width: 1.8;
}

.svg-lbl-nr {
  fill: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-lbl-pq {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
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
