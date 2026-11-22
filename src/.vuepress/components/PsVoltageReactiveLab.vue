<script setup lang="ts">
import { computed, ref } from "vue";

const emfE = ref(1.0); // Equivalent source EMF E (pu)
const xSys = ref(0.3); // Equivalent reactance X_Sigma (pu), matches Lec 10
const qLoad = ref(0.3); // Constant reactive load Q_D (pu)
const bCap = ref(0.0); // Shunt capacitor susceptance B_C (pu)

const applyPreset = (e: number, x: number, q: number, bc: number): void => {
  emfE.value = e;
  xSys.value = x;
  qLoad.value = q;
  bCap.value = bc;
};

const sim = computed(() => {
  const E = emfE.value;
  const X = xSys.value;
  const QD = qLoad.value;
  const Bc = bCap.value;

  // Net supply without cap: Q_net(U) = U(E - U)/X
  // Total supply with shunt cap: Q_sup(U) = U(E - U)/X + Bc*U^2 = (E/X)*U - (1/X - Bc)*U^2
  const a = 1 / X - Bc;
  const b = -E / X;
  const c = QD;

  let uHigh: number | null = null;
  let uLow: number | null = null;
  let qMax = Infinity;
  let uCrit = 0;

  if (a > 1e-4) {
    uCrit = -b / (2 * a);
    qMax = (E * E) / (4 * X * X * a);
    const disc = b * b - 4 * a * c;
    if (disc >= 0) {
      uHigh = (-b + Math.sqrt(disc)) / (2 * a);
      uLow = (-b - Math.sqrt(disc)) / (2 * a);
    }
  } else {
    // Degenerate over-compensated case
    uHigh = QD / (E / X);
  }

  const feasible = uHigh !== null && uHigh > 0;
  const uOp = uHigh ?? 0;
  const devPct = (uOp - 1) * 100;
  const qMargin = qMax - QD;
  const qCapAct = Bc * uOp * uOp;
  const qCapPct = Bc > 1e-5 ? uOp * uOp * 100 : 0;
  const qStatPct = Bc > 1e-5 ? uOp * 100 : 0;

  // Sample curves for U in [0, 1.3]
  const N = 130;
  const us: number[] = [];
  const qNetArr: number[] = [];
  const qTotArr: number[] = [];
  for (let i = 0; i <= N; i++) {
    const u = (1.3 * i) / N;
    const qn = (u * (E - u)) / X;
    us.push(u);
    qNetArr.push(qn);
    qTotArr.push(qn + Bc * u * u);
  }

  return {
    feasible,
    uHigh,
    uLow,
    uOp,
    devPct,
    qMax,
    uCrit,
    qMargin,
    qCapAct,
    qCapPct,
    qStatPct,
    us,
    qNetArr,
    qTotArr,
  };
});

// Left panel: Q-U curves
const W1 = 360;
const H1 = 220;
const qMaxAxis = 1.35;
const x1 = (u: number): number => 40 + (u / 1.3) * (W1 - 54);
const y1 = (q: number): number => H1 - 28 - (Math.max(-0.1, Math.min(qMaxAxis, q)) / qMaxAxis) * (H1 - 46);

const qNetPath = computed(() =>
  sim.value.us.map((u, i) => `${i === 0 ? "M" : "L"}${x1(u).toFixed(1)},${y1(sim.value.qNetArr[i]).toFixed(1)}`).join(" ")
);
const qTotPath = computed(() =>
  sim.value.us.map((u, i) => `${i === 0 ? "M" : "L"}${x1(u).toFixed(1)},${y1(sim.value.qTotArr[i]).toFixed(1)}`).join(" ")
);

// Right panel: Shunt Cap (U^2) vs Current-limited STATCOM (U)
const W2 = 280;
const H2 = 220;
const x2 = (u: number): number => 38 + (u / 1.2) * (W2 - 52);
const y2 = (r: number): number => H2 - 28 - (Math.min(1.45, r) / 1.45) * (H2 - 46);

const capRatioPath = computed(() => {
  const pts: string[] = [];
  for (let i = 0; i <= 60; i++) {
    const u = (1.2 * i) / 60;
    pts.push(`${i === 0 ? "M" : "L"}${x2(u).toFixed(1)},${y2(u * u).toFixed(1)}`);
  }
  return pts.join(" ");
});
const statRatioPath = computed(() => {
  const pts: string[] = [];
  for (let i = 0; i <= 60; i++) {
    const u = (1.2 * i) / 60;
    pts.push(`${i === 0 ? "M" : "L"}${x2(u).toFixed(1)},${y2(u).toFixed(1)}`);
  }
  return pts.join(" ");
});

const statusBadge = computed(() => {
  if (!sim.value.feasible) return { text: "无平衡交点 · 电压失稳崩溃!", cls: "is-bad" };
  if (Math.abs(sim.value.devPct) <= 5) return { text: `电压合格 (偏移 ${sim.value.devPct >= 0 ? "+" : ""}${sim.value.devPct.toFixed(1)}%)`, cls: "is-ok" };
  return { text: `电压越限 (偏移 ${sim.value.devPct >= 0 ? "+" : ""}${sim.value.devPct.toFixed(1)}%)`, cls: "is-warn" };
});
</script>

<template>
  <div class="ps-lab">
    <div class="ps-head">
      <div>
        <span class="ps-badge">交互实验 · INTERACTIVE LAB</span>
        <h4 class="ps-title">无功-电压 Q–U 平衡交点、励磁调压与并联电容特性实验室</h4>
      </div>
      <span class="ps-status" :class="statusBadge.cls">{{ statusBadge.text }}</span>
    </div>

    <div class="ps-presets">
      <button type="button" class="ps-chip" @click="applyPreset(1.0, 0.3, 0.3, 0.0)">基准工况 (E=1.0, Q_D=0.3)</button>
      <button type="button" class="ps-chip" @click="applyPreset(1.0, 0.3, 0.5, 0.0)">无功加重 (Q_D=0.5 电压跌落)</button>
      <button type="button" class="ps-chip" @click="applyPreset(1.1, 0.3, 0.5, 0.0)">发电机升励磁 (E=1.1 抬压)</button>
      <button type="button" class="ps-chip" @click="applyPreset(1.0, 0.3, 0.5, 0.45)">投入就地并联电容 (B_C=0.45)</button>
      <button type="button" class="ps-chip" @click="applyPreset(1.0, 0.3, 0.88, 0.0)">越过 Q_max (无交点崩溃!)</button>
    </div>

    <div class="ps-controls">
      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>电源等效电势 E</span>
          <strong>{{ emfE.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="emfE" type="range" min="0.88" max="1.20" step="0.01" />
      </label>

      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>负荷无功需求 Q<sub>D</sub></span>
          <strong>{{ qLoad.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="qLoad" type="range" min="0.05" max="1.10" step="0.01" />
      </label>

      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>就地并联电容电纳 B<sub>C</sub></span>
          <strong>{{ bCap.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="bCap" type="range" min="0.00" max="0.80" step="0.05" />
      </label>

      <label class="ps-slider">
        <span class="ps-slider-row">
          <span>通道总电抗 X<sub>Σ</sub></span>
          <strong>{{ xSys.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="xSys" type="range" min="0.18" max="0.50" step="0.02" />
      </label>
    </div>

    <div class="ps-grid">
      <!-- Q-U equilibrium -->
      <div class="ps-panel">
        <div class="ps-panel-label">无功供给 Q<sub>supply</sub>(U) 与需求 Q<sub>D</sub> 交点（实线含电容 / 虚线纯网络）</div>
        <svg :viewBox="`0 0 ${W1} ${H1}`" class="ps-svg">
          <!-- Allowed ±5% band -->
          <rect :x="x1(0.95)" y="16" :width="x1(1.05) - x1(0.95)" :height="H1 - 44" class="svg-ok-band" />
          <line x1="40" :y1="y1(0)" :x2="W1 - 14" :y2="y1(0)" class="svg-axis" />
          <line x1="40" y1="16" x2="40" :y2="H1 - 28" class="svg-axis" />
          <path :d="qNetPath" fill="none" class="svg-net" />
          <path :d="qTotPath" fill="none" class="svg-tot" />
          <!-- Load demand line -->
          <line x1="40" :y1="y1(qLoad)" :x2="W1 - 14" :y2="y1(qLoad)" class="svg-load" />
          <text :x="W1 - 16" :y="y1(qLoad) - 5" class="svg-load-lbl" text-anchor="end">Q_D = {{ qLoad.toFixed(2) }}</text>

          <!-- Low-voltage unstable intersection -->
          <circle v-if="sim.uLow !== null && sim.uLow > 0" :cx="x1(sim.uLow)" :cy="y1(qLoad)" r="4" class="svg-dot-low" />
          <!-- High-voltage operating intersection -->
          <circle v-if="sim.feasible" :cx="x1(sim.uOp)" :cy="y1(qLoad)" r="5.5" class="svg-dot-hi" />

          <text x="34" :y="y1(1.0) + 3" class="svg-tick" text-anchor="end">1.0</text>
          <text x="34" :y="y1(0.5) + 3" class="svg-tick" text-anchor="end">0.5</text>
          <text x="34" :y="y1(0) + 3" class="svg-tick" text-anchor="end">0</text>
          <text :x="x1(0.5)" :y="H1 - 10" class="svg-tick" text-anchor="middle">0.5</text>
          <text :x="x1(1.0)" :y="H1 - 10" class="svg-tick" text-anchor="middle">1.0 pu</text>
          <text :x="x1(1.2)" :y="H1 - 10" class="svg-tick" text-anchor="middle">1.2</text>
        </svg>
      </div>

      <!-- Capacitor U^2 vs STATCOM U -->
      <div class="ps-panel">
        <div class="ps-panel-label">低压支撑衰减对比：电容器 Q ∝ U² vs. 限流装置 Q ∝ U</div>
        <svg :viewBox="`0 0 ${W2} ${H2}`" class="ps-svg">
          <line x1="38" :y1="y2(1.0)" :x2="W2 - 14" :y2="y2(1.0)" class="svg-ref" />
          <line x1="38" y1="16" x2="38" :y2="H2 - 28" class="svg-axis" />
          <line x1="38" :y1="H2 - 28" :x2="W2 - 14" :y2="H2 - 28" class="svg-axis" />
          <path :d="statRatioPath" fill="none" class="svg-stat" />
          <path :d="capRatioPath" fill="none" class="svg-cap" />
          <template v-if="sim.feasible && sim.uOp <= 1.2">
            <line :x1="x2(sim.uOp)" y1="18" :x2="x2(sim.uOp)" :y2="H2 - 28" class="svg-ref" />
            <circle :cx="x2(sim.uOp)" :cy="y2(sim.uOp * sim.uOp)" r="4.5" class="svg-cap-dot" />
            <circle :cx="x2(sim.uOp)" :cy="y2(sim.uOp)" r="4.5" class="svg-stat-dot" />
          </template>
          <text x="33" :y="y2(1.0) + 3" class="svg-tick" text-anchor="end">100%</text>
          <text x="33" :y="y2(0.5) + 3" class="svg-tick" text-anchor="end">50%</text>
          <text :x="x2(0.7)" :y="H2 - 10" class="svg-tick" text-anchor="middle">0.7</text>
          <text :x="x2(1.0)" :y="H2 - 10" class="svg-tick" text-anchor="middle">1.0 pu</text>
          <text x="44" y="28" class="svg-lbl-stat">限流型 (∝U)</text>
          <text x="44" y="42" class="svg-lbl-cap">并联电容 (∝U²)</text>
        </svg>
      </div>
    </div>

    <div class="ps-metrics">
      <div class="ps-metric">
        <span>高电压运行点 U</span>
        <strong>{{ sim.feasible ? sim.uOp.toFixed(4) + " pu" : "无解 (崩溃)" }}</strong>
      </div>
      <div class="ps-metric">
        <span>极限无功 Q<sub>max</sub> / 裕度</span>
        <strong>{{ sim.qMax.toFixed(2) }} / {{ sim.qMargin >= 0 ? "+" : "" }}{{ sim.qMargin.toFixed(2) }} pu</strong>
      </div>
      <div class="ps-metric">
        <span>电容器实际发出 Q<sub>C</sub></span>
        <strong>{{ sim.qCapAct.toFixed(3) }} pu ({{ bCap > 0 ? sim.qCapPct.toFixed(0) + "%额定" : "未投入" }})</strong>
      </div>
      <div class="ps-metric">
        <span>当前电压下 U² vs U 支撑比</span>
        <strong>{{ sim.feasible ? `${(sim.uOp * sim.uOp * 100).toFixed(0)}% vs ${(sim.uOp * 100).toFixed(0)}%` : "—" }}</strong>
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

  &.is-warn {
    border: 1px solid #c27803;
    background: rgb(194 120 3 / 12%);
    color: #c27803;
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

  &:hover {
    border-color: var(--vp-c-accent);
    color: var(--vp-c-accent);
  }
}

.ps-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.6rem 1.1rem;
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

input[type="range"] {
  width: 100%;
  accent-color: var(--vp-c-accent);
  cursor: pointer;
}

.ps-grid {
  display: grid;
  grid-template-columns: 1.22fr 1fr;
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

.svg-ok-band {
  fill: #1e7a56;
  opacity: 0.1;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
}

.svg-ref {
  stroke: var(--vp-c-border);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-net {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-tot {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
}

.svg-load {
  stroke: #c83e37;
  stroke-width: 1.7;
}

.svg-load-lbl {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-dot-hi {
  fill: #1e7a56;
  stroke: var(--vp-c-bg);
  stroke-width: 1.8;
}

.svg-dot-low {
  fill: var(--vp-c-bg);
  stroke: #c83e37;
  stroke-width: 2;
}

.svg-cap {
  stroke: var(--vp-c-accent);
  stroke-width: 2.2;
}

.svg-stat {
  stroke: #1e7a56;
  stroke-width: 2.2;
  stroke-dasharray: 5 3;
}

.svg-cap-dot {
  fill: var(--vp-c-accent);
}

.svg-stat-dot {
  fill: #1e7a56;
}

.svg-lbl-stat {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
  font-weight: 600;
}

.svg-lbl-cap {
  fill: var(--vp-c-accent);
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
    font-size: 0.81rem;
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
