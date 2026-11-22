<script setup lang="ts">
import { computed, ref } from "vue";

// 4-pole, 50 Hz, 380 V (Y -> V_phi = 220 V) induction motor base params
const V_BASE = 220;
const F_BASE = 50;
const POLES = 4;
const R1 = 0.64;
const X1_BASE = 1.1;
const XM_BASE = 26.3;
const R2_BASE = 0.35;
const X2_BASE = 0.9;

const r2Mult = ref(1.0); // R2' / R2_base
const vRatio = ref(1.0); // V1 / V_base (used when constVf is off)
const freqHz = ref(50); // supply frequency f_e
const constVf = ref(false);
const loadTorque = ref(45); // N·m

const applyPreset = (r2m: number, vr: number, f: number, vf: boolean, tl: number): void => {
  r2Mult.value = r2m;
  vRatio.value = vr;
  freqHz.value = f;
  constVf.value = vf;
  loadTorque.value = tl;
};

const evaluateMotor = (r2m: number, vr: number, f: number) => {
  const fRatio = f / F_BASE;
  const Vphi = V_BASE * vr;
  const X1 = X1_BASE * fRatio;
  const Xm = XM_BASE * fRatio;
  const X2 = X2_BASE * fRatio;
  const R2 = R2_BASE * r2m;

  // Exact complex Thevenin equivalent: Zth = jXm*(R1+jX1) / (R1 + j(X1+Xm))
  const denRe = R1;
  const denIm = X1 + Xm;
  const den2 = denRe * denRe + denIm * denIm;
  const numRe = -Xm * X1;
  const numIm = Xm * R1;
  const Rth = (numRe * denRe + numIm * denIm) / den2;
  const Xth = (numIm * denRe - numRe * denIm) / den2;
  const Vth = (Vphi * Xm) / Math.sqrt(den2);

  const ns = (120 * f) / POLES;
  const ws = (2 * Math.PI * ns) / 60;

  const torqueAtSlip = (s: number): { tau: number; i2: number } => {
    if (s <= 1e-6) return { tau: 0, i2: 0 };
    const rTot = Rth + R2 / s;
    const xTot = Xth + X2;
    const i2 = Vth / Math.hypot(rTot, xTot);
    const tau = (3 * i2 * i2 * (R2 / s)) / ws;
    return { tau, i2 };
  };

  const zMag = Math.hypot(Rth, Xth + X2);
  const sMax = R2 / zMag;
  const tauMax = (3 * Vth * Vth) / (2 * ws * (Rth + zMag));
  const start = torqueAtSlip(1.0);

  // Sample curve n_m in [0, ns]
  const pts: { n: number; s: number; tau: number; i2: number }[] = [];
  const N = 120;
  for (let i = 0; i <= N; i++) {
    const s = 1 - i / N;
    const n = (1 - s) * ns;
    const { tau, i2 } = torqueAtSlip(s);
    pts.push({ n, s, tau, i2 });
  }

  return { ns, ws, sMax, tauMax, tauStart: start.tau, iStart: start.i2, pts, torqueAtSlip };
};

const effVRatio = computed(() => (constVf.value ? Math.min(1.05, freqHz.value / F_BASE) : vRatio.value));

const sim = computed(() => {
  const base = evaluateMotor(1.0, 1.0, F_BASE);
  const cur = evaluateMotor(r2Mult.value, effVRatio.value, freqHz.value);

  // Solve stable operating point on s in [0, min(1, sMax)]
  const sPeakClamped = Math.min(1.0, cur.sMax);
  const peakAvail = cur.torqueAtSlip(sPeakClamped).tau;
  const canRun = loadTorque.value <= peakAvail - 0.1;

  let sOp = 0;
  let nOp = 0;
  let i2Op = 0;
  let pAg = 0;
  let pRcl = 0;
  let pConv = 0;

  if (canRun) {
    let lo = 1e-5;
    let hi = sPeakClamped;
    for (let i = 0; i < 45; i++) {
      const mid = 0.5 * (lo + hi);
      if (cur.torqueAtSlip(mid).tau < loadTorque.value) lo = mid;
      else hi = mid;
    }
    sOp = 0.5 * (lo + hi);
    nOp = (1 - sOp) * cur.ns;
    const res = cur.torqueAtSlip(sOp);
    i2Op = res.i2;
    pAg = (res.tau * cur.ws) / 1000; // kW
    pRcl = sOp * pAg;
    pConv = (1 - sOp) * pAg;
  }

  return { base, cur, canRun, sOp, nOp, i2Op, pAg, pRcl, pConv };
});

// Left SVG: Torque-Speed
const TW = 370;
const TH = 224;
const nAxisMax = 1850;
const tAxisMax = 210;
const tx = (n: number): number => 42 + (Math.min(nAxisMax, n) / nAxisMax) * (TW - 56);
const ty = (tau: number): number => TH - 28 - (Math.min(tAxisMax, tau) / tAxisMax) * (TH - 46);

const baseTauPath = computed(() =>
  sim.value.base.pts.map((p, i) => `${i === 0 ? "M" : "L"}${tx(p.n).toFixed(1)},${ty(p.tau).toFixed(1)}`).join(" ")
);
const curTauPath = computed(() =>
  sim.value.cur.pts.map((p, i) => `${i === 0 ? "M" : "L"}${tx(p.n).toFixed(1)},${ty(p.tau).toFixed(1)}`).join(" ")
);

// Right SVG: Rotor current I2' vs speed + power split bar
const IW = 270;
const IH = 224;
const iAxisMax = 125;
const ix = (n: number): number => 38 + (Math.min(nAxisMax, n) / nAxisMax) * (IW - 50);
const iy = (iVal: number): number => 148 - (Math.min(iAxisMax, iVal) / iAxisMax) * 124;

const curI2Path = computed(() =>
  sim.value.cur.pts.map((p, i) => `${i === 0 ? "M" : "L"}${ix(p.n).toFixed(1)},${iy(p.i2).toFixed(1)}`).join(" ")
);
</script>

<template>
  <div class="em-lab">
    <div class="em-head">
      <div>
        <span class="em-badge">INTERACTIVE LAB</span>
        <h4 class="em-title">3-Phase Induction Motor Torque-Speed, Rotor Resistance &amp; V/f Speed Control</h4>
      </div>
      <span class="em-status" :class="sim.canRun ? 'is-ok' : 'is-bad'">
        {{ sim.canRun ? `Running · s = ${(sim.sOp * 100).toFixed(2)}% (${sim.nOp.toFixed(0)} RPM)` : "Stalled (Load Torque > τ_max)" }}
      </span>
    </div>

    <div class="em-presets">
      <button type="button" class="em-chip" @click="applyPreset(1.0, 1.0, 50, false, 45)">Rated Base (50 Hz, 1.0×R₂')</button>
      <button type="button" class="em-chip" @click="applyPreset(3.0, 1.0, 50, false, 45)">Added Rotor R (3×R₂' High Start Torque)</button>
      <button type="button" class="em-chip" @click="applyPreset(1.0, 0.7, 50, false, 45)">Reduced Voltage (0.7 V → τ ∝ V²)</button>
      <button type="button" class="em-chip" @click="applyPreset(1.0, 1.0, 30, true, 45)">Constant V/f Drive (30 Hz)</button>
      <button type="button" class="em-chip" @click="applyPreset(1.0, 1.0, 50, false, 160)">Overload Stall (τ_load = 160 N·m)</button>
    </div>

    <div class="em-controls">
      <label class="em-slider">
        <span class="em-slider-row">
          <span>Rotor Resistance Multiplier R<sub>2</sub>' / R<sub>2,base</sub>' (τ<sub>max</sub> invariant)</span>
          <strong>{{ r2Mult.toFixed(1) }}×</strong>
        </span>
        <input v-model.number="r2Mult" type="range" min="0.5" max="5.0" step="0.1" />
      </label>

      <label class="em-slider">
        <span class="em-slider-row">
          <span>Supply Frequency f<sub>e</sub> (n<sub>s</sub> = {{ sim.cur.ns.toFixed(0) }} RPM)</span>
          <strong>{{ freqHz }} Hz</strong>
        </span>
        <input v-model.number="freqHz" type="range" min="20" max="60" step="1" />
      </label>

      <label class="em-slider">
        <span class="em-slider-row">
          <span>Stator Voltage Ratio V<sub>1</sub> / V<sub>N</sub> {{ constVf ? "(locked to V/f)" : "" }}</span>
          <strong>{{ effVRatio.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="vRatio" type="range" min="0.45" max="1.10" step="0.05" :disabled="constVf" />
      </label>

      <div class="em-load-box">
        <label class="em-slider">
          <span class="em-slider-row">
            <span>Mechanical Load Torque τ<sub>load</sub></span>
            <strong>{{ loadTorque }} N·m</strong>
          </span>
          <input v-model.number="loadTorque" type="range" min="10" max="175" step="5" />
        </label>
        <label class="em-check">
          <input v-model="constVf" type="checkbox" />
          <span>Constant V/f Control (maintains constant air-gap flux Φ)</span>
        </label>
      </div>
    </div>

    <div class="em-grid">
      <!-- Torque-Speed Curve -->
      <div class="em-panel">
        <div class="em-panel-label">Torque-Speed τ<sub>ind</sub>(n<sub>m</sub>) (dashed: base, solid: current, red: load)</div>
        <svg :viewBox="`0 0 ${TW} ${TH}`" class="em-svg">
          <line x1="42" :y1="TH - 28" :x2="TW - 14" :y2="TH - 28" class="svg-ax" />
          <line x1="42" y1="16" x2="42" :y2="TH - 28" class="svg-ax" />
          <path :d="baseTauPath" fill="none" class="svg-base" />
          <path :d="curTauPath" fill="none" class="svg-cur" />
          <line x1="42" :y1="ty(loadTorque)" :x2="TW - 14" :y2="ty(loadTorque)" class="svg-load" />

          <!-- Pullout marker -->
          <circle
            v-if="sim.cur.sMax <= 1.0"
            :cx="tx((1 - sim.cur.sMax) * sim.cur.ns)"
            :cy="ty(sim.cur.tauMax)"
            r="4.2"
            class="svg-peak"
          />
          <!-- Operating point -->
          <circle v-if="sim.canRun" :cx="tx(sim.nOp)" :cy="ty(loadTorque)" r="5.5" class="svg-op" />

          <text x="36" :y="ty(200) + 4" class="svg-tick" text-anchor="end">200</text>
          <text x="36" :y="ty(100) + 4" class="svg-tick" text-anchor="end">100</text>
          <text x="36" :y="ty(0) + 3" class="svg-tick" text-anchor="end">0</text>
          <text v-for="n in [0, 500, 1000, 1500]" :key="n" :x="tx(n)" :y="TH - 10" class="svg-tick" text-anchor="middle">{{ n }}</text>
          <text :x="TW - 14" :y="TH - 10" class="svg-tick" text-anchor="end">RPM</text>
          <text :x="TW - 16" y="26" class="svg-lbl-pk" text-anchor="end">
            τ_max = {{ sim.cur.tauMax.toFixed(1) }} N·m @ s_max={{ (sim.cur.sMax * 100).toFixed(0) }}%
          </text>
        </svg>
      </div>

      <!-- Current & Power Split -->
      <div class="em-panel">
        <div class="em-panel-label">Referred Rotor Current I<sub>2</sub>'(n<sub>m</sub>) &amp; Power Split 1 : s : (1−s)</div>
        <svg :viewBox="`0 0 ${IW} ${IH}`" class="em-svg">
          <line x1="38" y1="148" :x2="IW - 12" y2="148" class="svg-ax" />
          <line x1="38" y1="20" x2="38" y2="148" class="svg-ax" />
          <path :d="curI2Path" fill="none" class="svg-i2" />
          <circle v-if="sim.canRun" :cx="ix(sim.nOp)" :cy="iy(sim.i2Op)" r="4.8" class="svg-op" />
          <text x="32" :y="iy(100) + 4" class="svg-tick" text-anchor="end">100A</text>
          <text x="32" :y="iy(50) + 4" class="svg-tick" text-anchor="end">50A</text>
          <text x="32" y="151" class="svg-tick" text-anchor="end">0</text>
          <text :x="IW - 14" y="28" class="svg-lbl-i2" text-anchor="end">I_start = {{ sim.cur.iStart.toFixed(1) }} A</text>

          <!-- Power flow split bar P_AG = P_conv + P_RCL -->
          <text x="12" y="176" class="svg-tick">Air-Gap Power Split: P_AG = P_conv (1−s) + P_RCL (s)</text>
          <rect x="12" y="184" :width="IW - 24" height="16" class="bar-bg" rx="2" />
          <template v-if="sim.canRun">
            <rect x="12" y="184" :width="(IW - 24) * (1 - sim.sOp)" height="16" class="bar-conv" rx="2" />
            <rect
              :x="12 + (IW - 24) * (1 - sim.sOp)"
              y="184"
              :width="(IW - 24) * sim.sOp"
              height="16"
              class="bar-rcl"
              rx="1"
            />
            <text x="12" y="214" class="svg-lbl-conv">P_conv {{ ((1 - sim.sOp) * 100).toFixed(1) }}%</text>
            <text :x="IW - 12" y="214" class="svg-lbl-rcl" text-anchor="end">P_RCL {{ (sim.sOp * 100).toFixed(1) }}%</text>
          </template>
        </svg>
      </div>
    </div>

    <div class="em-metrics">
      <div class="em-metric">
        <span>Starting Torque τ<sub>start</sub> (s = 1)</span>
        <strong>{{ sim.cur.tauStart.toFixed(1) }} N·m</strong>
      </div>
      <div class="em-metric">
        <span>Pullout τ<sub>max</sub> / s<sub>max</sub></span>
        <strong>{{ sim.cur.tauMax.toFixed(1) }} N·m / {{ (sim.cur.sMax * 100).toFixed(1) }}%</strong>
      </div>
      <div class="em-metric">
        <span>Running I<sub>2</sub>' / Starting I<sub>start</sub></span>
        <strong>{{ sim.canRun ? sim.i2Op.toFixed(1) : "Stalled" }} / {{ sim.cur.iStart.toFixed(1) }} A</strong>
      </div>
      <div class="em-metric">
        <span>P<sub>AG</sub> / P<sub>conv</sub> / P<sub>RCL</sub></span>
        <strong>{{ sim.canRun ? `${sim.pAg.toFixed(1)} / ${sim.pConv.toFixed(1)} / ${sim.pRcl.toFixed(2)} kW` : "—" }}</strong>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.em-lab {
  margin: 1.4rem 0;
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg-alt);
  font-size: 0.9rem;
  line-height: 1.5;
}

.em-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--vp-c-divider);
}

.em-badge {
  display: inline-block;
  color: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.em-title {
  margin: 0.15rem 0 0 !important;
  color: var(--ink);
  font-size: 1.02rem;
  font-weight: 700;
}

.em-status {
  padding: 0.2rem 0.62rem;
  border-radius: var(--r, 2px);
  font-family: var(--vp-font-mono);
  font-size: 0.75rem;
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

.em-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-bottom: 0.75rem;
}

.em-chip {
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

.em-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.62rem 1.1rem;
  margin-bottom: 0.85rem;
}

.em-slider,
.em-load-box {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
}

.em-slider-row {
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

.em-check {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  margin-top: 0.15rem;
  font-size: 0.79rem;
  cursor: pointer;
}

input[type="range"] {
  width: 100%;
  accent-color: var(--vp-c-accent);
  cursor: pointer;

  &:disabled {
    opacity: 0.35;
  }
}

.em-grid {
  display: grid;
  grid-template-columns: 1.25fr 0.95fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.em-panel {
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.em-panel-label {
  margin-bottom: 0.28rem;
  color: var(--vp-c-text-mute);
  font-size: 0.75rem;
  font-weight: 600;
}

.em-svg {
  display: block;
  width: 100%;
  height: auto;
}

.svg-ax {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
}

.svg-base {
  stroke: var(--vp-c-border);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-cur {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
}

.svg-load {
  stroke: #c83e37;
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-peak {
  fill: #c27803;
}

.svg-op {
  fill: #1e7a56;
  stroke: var(--vp-c-bg);
  stroke-width: 1.8;
}

.svg-i2 {
  stroke: #c27803;
  stroke-width: 2.2;
}

.bar-bg {
  fill: var(--vp-c-bg-alt);
}

.bar-conv {
  fill: #1e7a56;
  opacity: 0.85;
}

.bar-rcl {
  fill: #c83e37;
  opacity: 0.85;
}

.svg-lbl-pk {
  fill: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 9.2px;
  font-weight: 600;
}

.svg-lbl-i2 {
  fill: #c27803;
  font-family: var(--vp-font-mono);
  font-size: 9.2px;
  font-weight: 600;
}

.svg-lbl-conv {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 9px;
  font-weight: 600;
}

.svg-lbl-rcl {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 9px;
  font-weight: 600;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9.2px;
}

.em-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.48rem;
}

.em-metric {
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
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .em-controls,
  .em-grid {
    grid-template-columns: 1fr;
  }

  .em-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
