<script setup lang="ts">
import { computed, ref } from "vue";

type Topo = "buck" | "boost" | "buckboost";
const topo = ref<Topo>("boost");
const duty = ref(0.5);
const loadR = ref(20); // ohms
const indUh = ref(60); // uH
const fsKhz = 50; // 50 kHz
const vd = 24; // 24 V input

const solvePoint = (t: Topo, D: number, K: number) => {
  const L = indUh.value * 1e-6;
  const fs = fsKhz * 1e3;
  let kCrit = 1 - D;
  if (t === "boost") kCrit = D * (1 - D) * (1 - D);
  if (t === "buckboost") kCrit = (1 - D) * (1 - D);

  const isDcm = K < kCrit - 1e-6;
  const isBcm = Math.abs(K - kCrit) <= Math.max(0.015, kCrit * 0.04);

  let M = 1;
  let d1 = 1 - D;
  let d2 = 0;
  let iLMin = 0;
  let iLMax = 0;
  let vOn = 0;
  let vOff = 0;

  if (t === "buck") {
    if (!isDcm) {
      M = D;
      d1 = 1 - D;
      d2 = 0;
    } else {
      M = 2 / (1 + Math.sqrt(1 + (4 * K) / (D * D)));
      d1 = (D * (1 - M)) / M;
      d2 = Math.max(0, 1 - D - d1);
    }
    const vo = M * vd;
    const io = vo / loadR.value;
    const di = ((vd - vo) * D) / (fs * L);
    vOn = vd - vo;
    vOff = -vo;
    iLMin = isDcm ? 0 : Math.max(0, io - 0.5 * di);
    iLMax = isDcm ? di : io + 0.5 * di;
  } else if (t === "boost") {
    if (!isDcm) {
      M = 1 / (1 - D);
      d1 = 1 - D;
      d2 = 0;
    } else {
      M = (1 + Math.sqrt(1 + (4 * D * D) / K)) / 2;
      d1 = D / Math.max(1e-6, M - 1);
      d2 = Math.max(0, 1 - D - d1);
    }
    const vo = M * vd;
    const io = vo / loadR.value;
    const di = (vd * D) / (fs * L);
    const iLMean = isDcm ? 0.5 * di * (D + d1) : io / (1 - D);
    vOn = vd;
    vOff = vd - vo;
    iLMin = isDcm ? 0 : Math.max(0, iLMean - 0.5 * di);
    iLMax = isDcm ? di : iLMean + 0.5 * di;
  } else {
    if (!isDcm) {
      M = D / (1 - D);
      d1 = 1 - D;
      d2 = 0;
    } else {
      M = D / Math.sqrt(K);
      d1 = Math.sqrt(K);
      d2 = Math.max(0, 1 - D - d1);
    }
    const vo = M * vd;
    const io = vo / loadR.value;
    const di = (vd * D) / (fs * L);
    const iLMean = isDcm ? 0.5 * di * (D + d1) : io / (1 - D);
    vOn = vd;
    vOff = -vo;
    iLMin = isDcm ? 0 : Math.max(0, iLMean - 0.5 * di);
    iLMax = isDcm ? di : iLMean + 0.5 * di;
  }

  const vo = M * vd;
  const io = vo / loadR.value;
  // Exact CCM-DCM boundary output current I_oB = V_d * D * (1 - D) / (2 * f_s * L) for all three topologies
  const iOb = (vd * D * (1 - D)) / (2 * fs * L);
  return { M, vo, io, d1, d2, iLMin, iLMax, di: iLMax - iLMin, iOb, vOn, vOff, isDcm, isBcm, kCrit };
};

const Kval = computed(() => (2 * fsKhz * 1e3 * indUh.value * 1e-6) / loadR.value);
const state = computed(() => solvePoint(topo.value, duty.value, Kval.value));

const applyPreset = (t: Topo, d: number, r: number, l: number): void => {
  topo.value = t;
  duty.value = d;
  loadR.value = r;
  indUh.value = l;
};

// Waveform SVG (2 switching periods, t in [0, 2])
const WW = 370;
const WH = 220;
const wx = (t: number): number => 40 + (t / 2) * (WW - 54);
const wiY = (iVal: number, iTop: number): number => 112 - (iVal / iTop) * 84;
const wvY = (vVal: number, vAbs: number): number => 168 - (vVal / vAbs) * 34;

const waveData = computed(() => {
  const s = state.value;
  const D = duty.value;
  const iTop = Math.max(1.2, s.iLMax * 1.18);
  const vAbs = Math.max(12, Math.abs(s.vOn), Math.abs(s.vOff)) * 1.18;

  const iPts: string[] = [];
  const vPts: string[] = [];
  for (let p = 0; p < 2; p++) {
    const t0 = p;
    const t1 = p + D;
    const t2 = p + D + s.d1;
    const t3 = p + 1;

    if (p === 0) iPts.push(`M${wx(t0).toFixed(1)},${wiY(s.iLMin, iTop).toFixed(1)}`);
    iPts.push(`L${wx(t1).toFixed(1)},${wiY(s.iLMax, iTop).toFixed(1)}`);
    iPts.push(`L${wx(t2).toFixed(1)},${wiY(s.iLMin, iTop).toFixed(1)}`);
    if (s.d2 > 0.002) {
      iPts.push(`L${wx(t3).toFixed(1)},${wiY(0, iTop).toFixed(1)}`);
    }

    const cmd = p === 0 ? "M" : "L";
    vPts.push(`${cmd}${wx(t0).toFixed(1)},${wvY(s.vOn, vAbs).toFixed(1)}`);
    vPts.push(`L${wx(t1).toFixed(1)},${wvY(s.vOn, vAbs).toFixed(1)}`);
    vPts.push(`L${wx(t1).toFixed(1)},${wvY(s.vOff, vAbs).toFixed(1)}`);
    vPts.push(`L${wx(t2).toFixed(1)},${wvY(s.vOff, vAbs).toFixed(1)}`);
    if (s.d2 > 0.002) {
      vPts.push(`L${wx(t2).toFixed(1)},${wvY(0, vAbs).toFixed(1)}`);
      vPts.push(`L${wx(t3).toFixed(1)},${wvY(0, vAbs).toFixed(1)}`);
    }
  }
  return { iPath: iPts.join(" "), vPath: vPts.join(" "), iTop, vAbs };
});

// Gain curve SVG: |Vo|/Vd vs D in [0.05, 0.85]
const GW = 290;
const GH = 220;
const gMax = computed(() => (topo.value === "buck" ? 1.15 : 6.5));
const gx = (d: number): number => 38 + (d / 0.9) * (GW - 52);
const gy = (m: number): number => GH - 28 - (Math.min(gMax.value, m) / gMax.value) * (GH - 46);

const gainPaths = computed(() => {
  const ccmPts: string[] = [];
  const actPts: string[] = [];
  const steps = 80;
  for (let i = 0; i <= steps; i++) {
    const d = 0.05 + (0.8 * i) / steps;
    const mCcm = topo.value === "buck" ? d : topo.value === "boost" ? 1 / (1 - d) : d / (1 - d);
    const mAct = solvePoint(topo.value, d, Kval.value).M;
    ccmPts.push(`${i === 0 ? "M" : "L"}${gx(d).toFixed(1)},${gy(mCcm).toFixed(1)}`);
    actPts.push(`${i === 0 ? "M" : "L"}${gx(d).toFixed(1)},${gy(mAct).toFixed(1)}`);
  }
  return { ccm: ccmPts.join(" "), act: actPts.join(" ") };
});

const modeInfo = computed(() => {
  if (state.value.isBcm) return { text: "BCM (Boundary Conduction)", cls: "is-warn" };
  if (state.value.isDcm) return { text: "DCM (Discontinuous Conduction)", cls: "is-bad" };
  return { text: "CCM (Continuous Conduction)", cls: "is-ok" };
});
</script>

<template>
  <div class="pe-lab">
    <div class="pe-head">
      <div>
        <span class="pe-badge">INTERACTIVE LAB</span>
        <h4 class="pe-title">DC-DC Converter Volt-Second Balance &amp; CCM / DCM Transition (V<sub>d</sub> = 24 V, f<sub>s</sub> = 50 kHz)</h4>
      </div>
      <span class="pe-status" :class="modeInfo.cls">{{ modeInfo.text }}</span>
    </div>

    <div class="pe-presets">
      <button type="button" class="pe-chip" :class="{ 'is-active': topo === 'buck' }" @click="topo = 'buck'">Buck</button>
      <button type="button" class="pe-chip" :class="{ 'is-active': topo === 'boost' }" @click="topo = 'boost'">Boost</button>
      <button type="button" class="pe-chip" :class="{ 'is-active': topo === 'buckboost' }" @click="topo = 'buckboost'">Buck-Boost</button>
      <button type="button" class="pe-chip" @click="applyPreset('buck', 0.5, 10, 80)">Buck CCM</button>
      <button type="button" class="pe-chip" @click="applyPreset('buck', 0.4, 45, 40)">Buck Light-Load DCM</button>
      <button type="button" class="pe-chip" @click="applyPreset('boost', 0.5, 18, 60)">Boost CCM</button>
      <button type="button" class="pe-chip" @click="applyPreset('boost', 0.55, 95, 30)">Boost Light-Load DCM Surge</button>
    </div>

    <div class="pe-controls">
      <label class="pe-slider">
        <span class="pe-slider-row">
          <span>Duty Ratio D = t<sub>on</sub> / T<sub>s</sub></span>
          <strong>{{ duty.toFixed(2) }}</strong>
        </span>
        <input v-model.number="duty" type="range" min="0.08" max="0.82" step="0.01" />
      </label>

      <label class="pe-slider">
        <span class="pe-slider-row">
          <span>Load Resistance R (higher = lighter load)</span>
          <strong>{{ loadR }} Ω</strong>
        </span>
        <input v-model.number="loadR" type="range" min="4" max="120" step="1" />
      </label>

      <label class="pe-slider">
        <span class="pe-slider-row">
          <span>Inductance L (K = 2f<sub>s</sub>L/R = {{ Kval.toFixed(3) }})</span>
          <strong>{{ indUh }} μH</strong>
        </span>
        <input v-model.number="indUh" type="range" min="15" max="200" step="5" />
      </label>
    </div>

    <div class="dcdc-grid">
      <!-- Waveforms -->
      <div class="pe-panel">
        <div class="pe-panel-label">Inductor Current i<sub>L</sub>(t) (top, A) &amp; Voltage v<sub>L</sub>(t) (bottom, Area A = B)</div>
        <svg :viewBox="`0 0 ${WW} ${WH}`" class="pe-svg">
          <!-- iL zero line & axis -->
          <line x1="40" y1="112" :x2="WW - 12" y2="112" class="svg-axis" />
          <line x1="40" y1="18" x2="40" y2="114" class="svg-axis" />
          <path :d="waveData.iPath" fill="none" class="svg-il" />
          <text x="34" y="28" class="svg-tick" text-anchor="end">{{ waveData.iTop.toFixed(1) }}A</text>
          <text x="34" y="115" class="svg-tick" text-anchor="end">0</text>
          <text :x="WW - 14" y="26" class="svg-lbl-il" text-anchor="end">
            i_L: {{ state.iLMin.toFixed(2) }} → {{ state.iLMax.toFixed(2) }} A
          </text>

          <!-- vL zero line & axis -->
          <line x1="40" y1="168" :x2="WW - 12" y2="168" class="svg-axis" />
          <line x1="40" y1="130" x2="40" y2="206" class="svg-axis" />
          <path :d="waveData.vPath" fill="none" class="svg-vl" />
          <text x="34" y="171" class="svg-tick" text-anchor="end">0V</text>
          <text :x="wx(1)" y="216" class="svg-tick" text-anchor="middle">T_s</text>
          <text :x="wx(2)" y="216" class="svg-tick" text-anchor="middle">2T_s</text>
        </svg>
      </div>

      <!-- Voltage conversion ratio curve -->
      <div class="pe-panel">
        <div class="pe-panel-label">Voltage Gain |V<sub>o</sub>|/V<sub>d</sub> vs. D (dashed: CCM, solid: current K)</div>
        <svg :viewBox="`0 0 ${GW} ${GH}`" class="pe-svg">
          <line x1="38" :y1="GH - 28" :x2="GW - 12" :y2="GH - 28" class="svg-axis" />
          <line x1="38" y1="16" x2="38" :y2="GH - 28" class="svg-axis" />
          <path :d="gainPaths.ccm" fill="none" class="svg-ccm" />
          <path :d="gainPaths.act" fill="none" class="svg-act" />
          <circle :cx="gx(duty)" :cy="gy(state.M)" r="5" class="svg-dot" />
          <text x="32" :y="gy(1) + 3" class="svg-tick" text-anchor="end">1</text>
          <text x="32" :y="gy(gMax) + 6" class="svg-tick" text-anchor="end">{{ gMax.toFixed(1) }}</text>
          <text :x="gx(0.5)" :y="GH - 10" class="svg-tick" text-anchor="middle">D = 0.5</text>
          <text :x="GW - 14" :y="GH - 10" class="svg-tick" text-anchor="end">0.9</text>
          <text :x="GW - 16" y="28" class="svg-lbl-gain" text-anchor="end">
            M = {{ state.M.toFixed(2) }}
          </text>
        </svg>
      </div>
    </div>

    <div class="pe-metrics">
      <div class="pe-metric">
        <span>Output Voltage V<sub>o</sub></span>
        <strong>{{ topo === "buckboost" ? "−" : "" }}{{ state.vo.toFixed(1) }} V</strong>
      </div>
      <div class="pe-metric">
        <span>Output Current I<sub>o</sub> / Boundary I<sub>oB</sub></span>
        <strong>{{ state.io.toFixed(2) }} / {{ state.iOb.toFixed(2) }} A</strong>
      </div>
      <div class="pe-metric">
        <span>Inductor Ripple ΔI<sub>L</sub></span>
        <strong>{{ state.di.toFixed(2) }} A</strong>
      </div>
      <div class="pe-metric">
        <span>Subintervals D / Δ<sub>1</sub> / Δ<sub>2</sub></span>
        <strong>{{ duty.toFixed(2) }} / {{ state.d1.toFixed(2) }} / {{ state.d2.toFixed(2) }}</strong>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.pe-lab {
  margin: 1.4rem 0;
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg-alt);
  font-size: 0.9rem;
  line-height: 1.5;
}

.pe-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--vp-c-divider);
}

.pe-badge {
  display: inline-block;
  color: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.pe-title {
  margin: 0.15rem 0 0 !important;
  color: var(--ink);
  font-size: 1.02rem;
  font-weight: 700;
}

.pe-status {
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

.pe-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-bottom: 0.75rem;
}

.pe-chip {
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

.pe-controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem 1rem;
  margin-bottom: 0.85rem;
}

.pe-slider {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
}

.pe-slider-row {
  display: flex;
  justify-content: space-between;
  gap: 0.4rem;
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

.dcdc-grid {
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.pe-panel {
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.pe-panel-label {
  margin-bottom: 0.3rem;
  color: var(--vp-c-text-mute);
  font-size: 0.75rem;
  font-weight: 600;
}

.pe-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-axis {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
}

.svg-il {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
  stroke-linejoin: round;
}

.svg-vl {
  stroke: #1e7a56;
  stroke-width: 2;
  stroke-linejoin: round;
}

.svg-ccm {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-act {
  stroke: #c83e37;
  stroke-width: 2.2;
}

.svg-dot {
  fill: var(--vp-c-accent);
  stroke: var(--vp-c-bg);
  stroke-width: 1.8;
}

.svg-lbl-il,
.svg-lbl-gain {
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

.pe-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.48rem;
}

.pe-metric {
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
    font-size: 0.82rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .pe-controls,
  .dcdc-grid {
    grid-template-columns: 1fr;
  }

  .pe-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
