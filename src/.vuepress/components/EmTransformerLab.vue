<script setup lang="ts">
import { computed, ref } from "vue";

// Per-unit transformer model: V2_rated = 1.0 pu, Req = 0.015 pu, Xeq = 0.06 pu (adjustable)
// Loss parameters at rated S_N = 100 kVA: P_0 = 0.6 kW (0.6%), P_kN = 1.8 kW (1.8%)
const loadBeta = ref(0.8); // Load factor beta = I2 / I2N in [0.05, 1.4]
const pfAngleDeg = ref(36.9); // phi2 > 0 lagging (inductive), < 0 leading (capacitive)
const p0Pct = ref(0.6); // Core loss P0 (% of S_N)
const pkPct = ref(1.8); // Full-load copper loss PkN (% of S_N)

const applyPreset = (b: number, phi: number, p0: number, pk: number): void => {
  loadBeta.value = b;
  pfAngleDeg.value = phi;
  p0Pct.value = p0;
  pkPct.value = pk;
};

const sim = computed(() => {
  const beta = loadBeta.value;
  const phiRad = (pfAngleDeg.value * Math.PI) / 180;
  const cosPhi = Math.cos(phiRad);
  const sinPhi = Math.sin(phiRad);

  // Per-unit series impedance: Req matches pkPct/100, Xeq = 0.08 pu (exaggerated gently on phasor for clarity)
  const Req = pkPct.value / 100;
  const Xeq = 0.08;

  // Referred primary voltage V1' = V2 + I2*(Req + j*Xeq), with V2 = 1∠0° and I2 = beta*(cosPhi - j*sinPhi)
  const iRe = beta * cosPhi;
  const iIm = -beta * sinPhi;
  // Drop = I2*(Req + jXeq) = (iRe*Req - iIm*Xeq) + j*(iRe*Xeq + iIm*Req)
  const dRe = iRe * Req - iIm * Xeq;
  const dIm = iRe * Xeq + iIm * Req;
  const v1Re = 1 + dRe;
  const v1Im = dIm;
  const v1Mag = Math.hypot(v1Re, v1Im);
  const vrPct = (v1Mag - 1) * 100;

  // Efficiency eta(beta) = (beta*cosPhi) / (beta*cosPhi + P0 + beta^2*PkN)
  const p0 = p0Pct.value / 100;
  const pk = pkPct.value / 100;
  const etaAt = (b: number): number => {
    const pout = b * Math.max(0.05, cosPhi);
    return (pout / (pout + p0 + b * b * pk)) * 100;
  };
  const etaCur = etaAt(beta);
  const betaOpt = Math.sqrt(p0 / pk);
  const etaMax = etaAt(betaOpt);

  // Sweep beta in [0.05, 1.4] for efficiency curve & loss curves
  const betas: number[] = [];
  const etas: number[] = [];
  const etasUnity: number[] = [];
  for (let i = 0; i <= 68; i++) {
    const b = 0.05 + (1.35 * i) / 68;
    betas.push(b);
    etas.push(etaAt(b));
    etasUnity.push((b / (b + p0 + b * b * pk)) * 100);
  }

  return {
    cosPhi,
    Req,
    Xeq,
    iRe,
    iIm,
    dRe,
    dIm,
    v1Re,
    v1Im,
    v1Mag,
    vrPct,
    p0Cur: p0 * 100,
    pCuCur: beta * beta * pk * 100,
    etaCur,
    betaOpt,
    etaMax,
    betas,
    etas,
    etasUnity,
  };
});

// Left SVG: Phasor Diagram (zoomed view of impedance triangle near V2 tip for crystal clarity)
const PW = 295;
const PH = 215;
const pox = 36;
const poy = 122;
const psc = 155; // 1 pu -> 155 px, plus 3× magnified impedance drop visual
const dropScale = 2.6;

const v2x = pox + 1.0 * psc;
const v2y = poy;
const rTipX = computed(() => v2x + sim.value.iRe * sim.value.Req * psc * dropScale);
const rTipY = computed(() => v2y - sim.value.iIm * sim.value.Req * psc * dropScale);
const v1x = computed(() => v2x + sim.value.dRe * psc * dropScale);
const v1y = computed(() => v2y - sim.value.dIm * psc * dropScale);
const ix = computed(() => pox + sim.value.iRe * 70);
const iy = computed(() => poy - sim.value.iIm * 70);

// Right SVG: Efficiency curve eta(beta)
const EW = 345;
const EH = 215;
const ex = (b: number): number => 44 + (b / 1.45) * (EW - 58);
const ey = (eta: number): number => 16 + ((100 - Math.max(82, Math.min(100, eta))) / 18) * (EH - 44);

const etaPath = computed(() =>
  sim.value.betas.map((b, i) => `${i === 0 ? "M" : "L"}${ex(b).toFixed(1)},${ey(sim.value.etas[i]).toFixed(1)}`).join(" ")
);
const etaUnityPath = computed(() =>
  sim.value.betas.map((b, i) => `${i === 0 ? "M" : "L"}${ex(b).toFixed(1)},${ey(sim.value.etasUnity[i]).toFixed(1)}`).join(" ")
);

const vrStatus = computed(() => {
  if (sim.value.vrPct < -0.1) return { text: `Negative VR = ${sim.value.vrPct.toFixed(2)}% (Leading Boost)`, cls: "is-warn" };
  return { text: `Voltage Regulation VR = +${sim.value.vrPct.toFixed(2)}%`, cls: "is-ok" };
});
</script>

<template>
  <div class="em-lab">
    <div class="em-head">
      <div>
        <span class="em-badge">INTERACTIVE LAB</span>
        <h4 class="em-title">Transformer Phasor Diagram, Voltage Regulation (VR) &amp; Efficiency η(β)</h4>
      </div>
      <span class="em-status" :class="vrStatus.cls">{{ vrStatus.text }}</span>
    </div>

    <div class="em-presets">
      <button type="button" class="em-chip" @click="applyPreset(1.0, 36.9, 0.6, 1.8)">Full Load Lagging (0.8 PF)</button>
      <button type="button" class="em-chip" @click="applyPreset(1.0, 0, 0.6, 1.8)">Full Load Unity (1.0 PF)</button>
      <button type="button" class="em-chip" @click="applyPreset(1.0, -36.9, 0.6, 1.8)">Full Load Leading (0.8 PF → VR &lt; 0)</button>
      <button type="button" class="em-chip" @click="applyPreset(0.577, 0, 0.6, 1.8)">Max Efficiency β_m = √(P₀/P_kN)</button>
    </div>

    <div class="em-controls">
      <label class="em-slider">
        <span class="em-slider-row">
          <span>Load Factor β = I<sub>2</sub> / I<sub>2N</sub></span>
          <strong>{{ loadBeta.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="loadBeta" type="range" min="0.08" max="1.40" step="0.02" />
      </label>

      <label class="em-slider">
        <span class="em-slider-row">
          <span>Power Factor Angle φ<sub>2</sub> (&gt;0 lagging / &lt;0 leading)</span>
          <strong>{{ pfAngleDeg.toFixed(1) }}° (cosφ = {{ sim.cosPhi.toFixed(2) }})</strong>
        </span>
        <input v-model.number="pfAngleDeg" type="range" min="-60" max="60" step="1" />
      </label>

      <label class="em-slider">
        <span class="em-slider-row">
          <span>Core Loss P<sub>0</sub> (% S<sub>N</sub>, constant)</span>
          <strong>{{ p0Pct.toFixed(2) }}%</strong>
        </span>
        <input v-model.number="p0Pct" type="range" min="0.2" max="1.6" step="0.1" />
      </label>

      <label class="em-slider">
        <span class="em-slider-row">
          <span>Rated Copper Loss P<sub>kN</sub> (% S<sub>N</sub>, scales as β²)</span>
          <strong>{{ pkPct.toFixed(2) }}%</strong>
        </span>
        <input v-model.number="pkPct" type="range" min="0.8" max="3.6" step="0.2" />
      </label>
    </div>

    <div class="em-grid">
      <!-- Phasor Diagram -->
      <div class="em-panel">
        <div class="em-panel-label">Phasor Diagram (impedance drop scaled 2.6× for clarity)</div>
        <svg :viewBox="`0 0 ${PW} ${PH}`" class="em-svg">
          <!-- Unit circle arc showing |V2| = 1 reference -->
          <circle :cx="pox" :cy="poy" :r="psc" fill="none" class="svg-arc" />
          <line x1="12" :y1="poy" :x2="PW - 10" :y2="poy" class="svg-ax" />
          <line :x1="pox" y1="14" :x2="pox" :y2="PH - 14" class="svg-ax" />

          <!-- V2 -->
          <line :x1="pox" :y1="poy" :x2="v2x" :y2="v2y" class="svg-v2" />
          <text :x="v2x - 8" :y="v2y + 14" class="svg-lbl-v2" text-anchor="end">V₂</text>
          <!-- I2 -->
          <line :x1="pox" :y1="poy" :x2="ix" :y2="iy" class="svg-i2" />
          <circle :cx="ix" :cy="iy" r="3.5" class="svg-i2-dot" />
          <text :x="ix + 5" :y="iy + (iy > poy ? 11 : -5)" class="svg-lbl-i2">I₂</text>
          <!-- I2*Req -->
          <line :x1="v2x" :y1="v2y" :x2="rTipX" :y2="rTipY" class="svg-ir" />
          <!-- j*I2*Xeq -->
          <line :x1="rTipX" :y1="rTipY" :x2="v1x" :y2="v1y" class="svg-ix" />
          <!-- V1' -->
          <line :x1="pox" :y1="poy" :x2="v1x" :y2="v1y" class="svg-v1" />
          <circle :cx="v1x" :cy="v1y" r="4" class="svg-v1-dot" />
          <text :x="v1x + 5" :y="v1y - 6" class="svg-lbl-v1">V₁'</text>
          <text :x="PW - 10" y="24" class="svg-tick" text-anchor="end">Dashed: |V₂| = 1</text>
        </svg>
      </div>

      <!-- Efficiency curve -->
      <div class="em-panel">
        <div class="em-panel-label">Efficiency η(β) (solid: current cosφ, dashed: unity PF, line: β<sub>m</sub>)</div>
        <svg :viewBox="`0 0 ${EW} ${EH}`" class="em-svg">
          <line x1="44" y1="16" x2="44" :y2="EH - 28" class="svg-ax" />
          <line x1="44" :y1="EH - 28" :x2="EW - 14" :y2="EH - 28" class="svg-ax" />
          <!-- Optimal beta_m line -->
          <line v-if="sim.betaOpt <= 1.45" :x1="ex(sim.betaOpt)" y1="16" :x2="ex(sim.betaOpt)" :y2="EH - 28" class="svg-opt-line" />
          <path :d="etaUnityPath" fill="none" class="svg-unity" />
          <path :d="etaPath" fill="none" class="svg-eta" />
          <circle :cx="ex(loadBeta)" :cy="ey(sim.etaCur)" r="5" class="svg-op" />

          <text v-for="v in [100, 94, 88, 82]" :key="v" x="38" :y="ey(v) + 3" class="svg-tick" text-anchor="end">{{ v }}%</text>
          <text v-for="b in [0.2, 0.6, 1.0, 1.4]" :key="b" :x="ex(b)" :y="EH - 10" class="svg-tick" text-anchor="middle">{{ b }}</text>
          <text v-if="sim.betaOpt <= 1.45" :x="ex(sim.betaOpt) + 4" y="28" class="svg-lbl-opt">β_m={{ sim.betaOpt.toFixed(2) }}</text>
        </svg>
      </div>
    </div>

    <div class="em-metrics">
      <div class="em-metric">
        <span>Efficiency η / Peak η<sub>max</sub></span>
        <strong>{{ sim.etaCur.toFixed(2) }}% / {{ sim.etaMax.toFixed(2) }}%</strong>
      </div>
      <div class="em-metric">
        <span>Optimal Load β<sub>m</sub> = √(P<sub>0</sub>/P<sub>kN</sub>)</span>
        <strong>{{ sim.betaOpt.toFixed(3) }}</strong>
      </div>
      <div class="em-metric">
        <span>Core P<sub>Fe</sub> vs. Copper β²P<sub>kN</sub></span>
        <strong>{{ sim.p0Cur.toFixed(2) }}% vs {{ sim.pCuCur.toFixed(2) }}%</strong>
      </div>
      <div class="em-metric">
        <span>Voltage Regulation VR</span>
        <strong>{{ sim.vrPct >= 0 ? "+" : "" }}{{ sim.vrPct.toFixed(2) }}%</strong>
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

  &.is-warn {
    border: 1px solid #c27803;
    background: rgb(194 120 3 / 12%);
    color: #c27803;
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
  gap: 0.6rem 1.1rem;
  margin-bottom: 0.85rem;
}

.em-slider {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.em-slider-row {
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

.em-grid {
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
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
  stroke-width: 0.9;
}

.svg-arc {
  stroke: var(--vp-c-border);
  stroke-width: 1.1;
  stroke-dasharray: 4 3;
}

.svg-v2 {
  stroke: var(--ink);
  stroke-width: 2.3;
}

.svg-i2 {
  stroke: #1e7a56;
  stroke-width: 2;
}

.svg-i2-dot {
  fill: #1e7a56;
}

.svg-ir {
  stroke: #c27803;
  stroke-width: 2;
}

.svg-ix {
  stroke: #c83e37;
  stroke-width: 2;
}

.svg-v1,
.svg-eta {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
}

.svg-v1-dot,
.svg-op {
  fill: var(--vp-c-accent);
  stroke: var(--vp-c-bg);
  stroke-width: 1.5;
}

.svg-unity {
  stroke: var(--vp-c-border);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-opt-line {
  stroke: #1e7a56;
  stroke-width: 1.2;
  stroke-dasharray: 3 3;
}

.svg-lbl-v2 {
  fill: var(--ink);
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 700;
}

.svg-lbl-v1 {
  fill: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 700;
}

.svg-lbl-i2 {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 700;
}

.svg-lbl-opt {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
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
    font-size: 0.8rem;
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
