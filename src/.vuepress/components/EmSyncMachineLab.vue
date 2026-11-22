<script setup lang="ts">
import { computed, ref } from "vue";

const rotorType = ref<"cylindrical" | "salient">("salient");
const pOut = ref(0.6); // pu active power
const emfE0 = ref(1.35); // pu excitation EMF E_0
const rightTab = ref<"power" | "vcurve">("power");

const applyPreset = (type: "cylindrical" | "salient", p: number, e: number, tab: "power" | "vcurve"): void => {
  rotorType.value = type;
  pOut.value = p;
  emfE0.value = e;
  rightTab.value = tab;
};

const solveSync = (E: number, P: number, Xd: number, Xq: number) => {
  const V = 1.0;
  const pField = (d: number) => ((E * V) / Xd) * Math.sin(d);
  const pRel = (d: number) => ((V * V * (Xd - Xq)) / (2 * Xd * Xq)) * Math.sin(2 * d);
  const pTot = (d: number) => pField(d) + pRel(d);

  // Locate P_max and delta_max on [0, pi/2]
  let dMax = Math.PI / 2;
  let pMax = pTot(dMax);
  for (let i = 1; i <= 180; i++) {
    const d = (Math.PI / 2) * (i / 180);
    const val = pTot(d);
    if (val > pMax) {
      pMax = val;
      dMax = d;
    }
  }

  const stable = P <= pMax - 1e-4;
  let delta = dMax;
  if (stable) {
    let lo = 0;
    let hi = dMax;
    for (let i = 0; i < 50; i++) {
      const mid = 0.5 * (lo + hi);
      if (pTot(mid) < P) lo = mid;
      else hi = mid;
    }
    delta = 0.5 * (lo + hi);
  }

  const Id = (E - V * Math.cos(delta)) / Xd;
  const Iq = (V * Math.sin(delta)) / Xq;
  const Ia = Math.hypot(Id, Iq);
  const Q = (E * V * Math.cos(delta) - V * V * Math.cos(delta) * Math.cos(delta)) / Xd - (V * V * Math.sin(delta) * Math.sin(delta)) / Xq;
  const phiRad = Math.atan2(Q, Math.max(1e-6, P)); // >0 lagging (overexcited)
  const pf = Math.cos(phiRad);

  // Phasor coordinates in V = 1∠0° frame:
  // q-axis unit = (cos d, sin d), d-axis unit = (sin d, -cos d)
  const cd = Math.cos(delta);
  const sd = Math.sin(delta);
  const Evec = { x: E * cd, y: E * sd };
  const Ivec = { x: Iq * cd + Id * sd, y: Iq * sd - Id * cd };
  const IdVec = { x: Id * sd, y: -Id * cd };
  const IqVec = { x: Iq * cd, y: Iq * sd };
  // j*Iq*Xq is along -d-axis = (-sin d, cos d), j*Id*Xd is along +q-axis = (cos d, sin d)
  const jIqXq = { x: -Iq * Xq * sd, y: Iq * Xq * cd };
  const jIdXd = { x: Id * Xd * cd, y: Id * Xd * sd };

  return {
    stable,
    delta,
    deltaDeg: (delta * 180) / Math.PI,
    dMaxDeg: (dMax * 180) / Math.PI,
    pMax,
    Id,
    Iq,
    Ia,
    Q,
    pf,
    phiDeg: (phiRad * 180) / Math.PI,
    Evec,
    Ivec,
    IdVec,
    IqVec,
    jIqXq,
    jIdXd,
    pField,
    pRel,
    pTot,
  };
};

const sim = computed(() => {
  const Xd = rotorType.value === "salient" ? 1.1 : 1.0;
  const Xq = rotorType.value === "salient" ? 0.65 : 1.0;
  const res = solveSync(emfE0.value, pOut.value, Xd, Xq);

  // Power-angle curves on [0, 180°]
  const degs: number[] = [];
  const pTotArr: number[] = [];
  const pFldArr: number[] = [];
  const pRelArr: number[] = [];
  for (let d = 0; d <= 180; d += 2) {
    const rad = (d * Math.PI) / 180;
    degs.push(d);
    pTotArr.push(res.pTot(rad));
    pFldArr.push(res.pField(rad));
    pRelArr.push(res.pRel(rad));
  }

  // V-curve sweep E in [0.55, 2.0] for current P and reference P=0.3, 0.9
  const makeVCurve = (pTarget: number) => {
    const pts: { e: number; ia: number }[] = [];
    for (let i = 0; i <= 75; i++) {
      const e = 0.55 + (1.45 * i) / 75;
      const r = solveSync(e, pTarget, Xd, Xq);
      if (r.stable && r.Ia <= 2.2) pts.push({ e, ia: r.Ia });
    }
    return pts;
  };

  return {
    Xd,
    Xq,
    ...res,
    degs,
    pTotArr,
    pFldArr,
    pRelArr,
    vMain: makeVCurve(pOut.value),
    vLow: makeVCurve(0.3),
    vHi: makeVCurve(0.9),
  };
});

// Left SVG: Phasor Diagram
const PW = 290;
const PH = 232;
const ox = 64;
const oy = 148;
const sc = 92; // pixels per pu
const px = (x: number): number => ox + x * sc;
const py = (y: number): number => oy - y * sc;

// Right SVG: Power-Angle or V-Curve
const RW = 350;
const RH = 232;
const paX = (deg: number): number => 40 + (deg / 180) * (RW - 56);
const paY = (p: number): number => 192 - (p / 2.2) * 168;

const paPath = (arr: number[]): string =>
  sim.value.degs.map((d, i) => `${i === 0 ? "M" : "L"}${paX(d).toFixed(1)},${paY(arr[i]).toFixed(1)}`).join(" ");

const vcX = (e: number): number => 42 + ((e - 0.5) / 1.55) * (RW - 56);
const vcY = (ia: number): number => RH - 28 - (Math.min(1.9, ia) / 1.9) * (RH - 46);
const vcPath = (pts: { e: number; ia: number }[]): string =>
  pts.map((pt, i) => `${i === 0 ? "M" : "L"}${vcX(pt.e).toFixed(1)},${vcY(pt.ia).toFixed(1)}`).join(" ");

const excState = computed(() => {
  if (!sim.value.stable) return { text: "Loss of Synchronism (P > P_max)", cls: "is-bad" };
  if (sim.value.Q > 0.04) return { text: "Overexcited (Lagging PF · Supplying Q · Demagnetizing)", cls: "is-ok" };
  if (sim.value.Q < -0.04) return { text: "Underexcited (Leading PF · Absorbing Q · Magnetizing)", cls: "is-warn" };
  return { text: "Normal Excitation (cosφ ≈ 1, Q ≈ 0)", cls: "is-ok" };
});
</script>

<template>
  <div class="em-lab">
    <div class="em-head">
      <div>
        <span class="em-badge">INTERACTIVE LAB</span>
        <h4 class="em-title">Synchronous Generator on an Infinite Bus: Phasor, P(δ) &amp; V-Curves</h4>
      </div>
      <span class="em-status" :class="excState.cls">{{ excState.text }}</span>
    </div>

    <div class="em-presets">
      <button type="button" class="em-chip" :class="{ 'is-active': rotorType === 'cylindrical' }" @click="rotorType = 'cylindrical'">
        Cylindrical (Xd = Xq = 1.0)
      </button>
      <button type="button" class="em-chip" :class="{ 'is-active': rotorType === 'salient' }" @click="rotorType = 'salient'">
        Salient-Pole (Xd = 1.1, Xq = 0.65)
      </button>
      <button type="button" class="em-chip" @click="applyPreset('salient', 0.6, 1.55, 'vcurve')">Overexcited (+Q, Right V-Branch)</button>
      <button type="button" class="em-chip" @click="applyPreset('salient', 0.6, 0.85, 'vcurve')">Underexcited (−Q, Left V-Branch)</button>
      <button type="button" class="em-chip" @click="applyPreset('salient', 0.75, 1.15, 'power')">Salient Reluctance Power (δ_max &lt; 90°)</button>
    </div>

    <div class="em-controls-2">
      <label class="em-slider">
        <span class="em-slider-row">
          <span>Active Power Output P (Governor Control)</span>
          <strong>{{ pOut.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="pOut" type="range" min="0.05" max="1.45" step="0.02" />
      </label>

      <label class="em-slider">
        <span class="em-slider-row">
          <span>Excitation EMF E<sub>0</sub> (Field Current I<sub>f</sub> Control)</span>
          <strong>{{ emfE0.toFixed(2) }} pu</strong>
        </span>
        <input v-model.number="emfE0" type="range" min="0.60" max="1.95" step="0.02" />
      </label>
    </div>

    <div class="em-grid">
      <!-- Phasor Diagram -->
      <div class="em-panel">
        <div class="em-panel-label">Phasor Diagram (V<sub>φ</sub>=1∠0°, blue: E<sub>0</sub>, green: I<sub>A</sub>, dashed: jI<sub>q</sub>X<sub>q</sub> / jI<sub>d</sub>X<sub>d</sub>)</div>
        <svg :viewBox="`0 0 ${PW} ${PH}`" class="em-svg">
          <defs>
            <clipPath id="sync-phasor-clip">
              <rect x="8" y="8" :width="PW - 16" :height="PH - 16" />
            </clipPath>
          </defs>
          <g clip-path="url(#sync-phasor-clip)">
            <line x1="12" :y1="oy" :x2="PW - 12" :y2="oy" class="svg-ax" />
            <line :x1="ox" y1="12" :x2="ox" :y2="PH - 12" class="svg-ax" />

            <!-- V_phi = 1∠0° -->
            <line :x1="ox" :y1="oy" :x2="px(1)" :y2="py(0)" class="svg-v" />
            <circle :cx="px(1)" :cy="py(0)" r="3.5" class="svg-v-dot" />
            <text :x="px(1) + 5" :y="py(0) + 12" class="svg-lbl-v">V_φ</text>

            <template v-if="sim.stable">
              <!-- jIqXq from tip of V -->
              <line :x1="px(1)" :y1="py(0)" :x2="px(1 + sim.jIqXq.x)" :y2="py(sim.jIqXq.y)" class="svg-drop-q" />
              <!-- jIdXd from V + jIqXq to E0 -->
              <line :x1="px(1 + sim.jIqXq.x)" :y1="py(sim.jIqXq.y)" :x2="px(sim.Evec.x)" :y2="py(sim.Evec.y)" class="svg-drop-d" />
              <!-- E0 -->
              <line :x1="ox" :y1="oy" :x2="px(sim.Evec.x)" :y2="py(sim.Evec.y)" class="svg-e0" />
              <circle :cx="px(sim.Evec.x)" :cy="py(sim.Evec.y)" r="4" class="svg-e0-dot" />
              <text :x="px(sim.Evec.x) + 6" :y="py(sim.Evec.y) - 4" class="svg-lbl-e0">E₀</text>
              <!-- I_A -->
              <line :x1="ox" :y1="oy" :x2="px(sim.Ivec.x)" :y2="py(sim.Ivec.y)" class="svg-ia" />
              <circle :cx="px(sim.Ivec.x)" :cy="py(sim.Ivec.y)" r="3.8" class="svg-ia-dot" />
              <text :x="px(sim.Ivec.x) + 5" :y="py(sim.Ivec.y) + (sim.Ivec.y < 0 ? 12 : -5)" class="svg-lbl-ia">I_A</text>
            </template>
          </g>
        </svg>
      </div>

      <!-- Right Panel: Power-Angle or V-Curve -->
      <div class="em-panel">
        <div class="em-panel-head-row">
          <span class="em-panel-label">
            {{ rightTab === "power" ? "Power-Angle Curve P(δ) (with sin 2δ reluctance term)" : "V-Curves: Armature Current I_A vs. E₀" }}
          </span>
          <div class="em-mini-tabs">
            <button type="button" class="em-mini" :class="{ 'is-active': rightTab === 'power' }" @click="rightTab = 'power'">P–δ Curve</button>
            <button type="button" class="em-mini" :class="{ 'is-active': rightTab === 'vcurve' }" @click="rightTab = 'vcurve'">V-Curves</button>
          </div>
        </div>

        <svg v-if="rightTab === 'power'" :viewBox="`0 0 ${RW} ${RH}`" class="em-svg">
          <line x1="40" :y1="paY(0)" :x2="RW - 16" :y2="paY(0)" class="svg-ax" />
          <line x1="40" y1="16" x2="40" :y2="RH - 24" class="svg-ax" />
          <line :x1="paX(90)" y1="16" :x2="paX(90)" :y2="paY(0)" class="svg-guide" />
          <line x1="40" :y1="paY(pOut)" :x2="RW - 16" :y2="paY(pOut)" class="svg-pm" />
          <path :d="paPath(sim.pFldArr)" fill="none" class="svg-pfld" />
          <path v-if="rotorType === 'salient'" :d="paPath(sim.pRelArr)" fill="none" class="svg-prel" />
          <path :d="paPath(sim.pTotArr)" fill="none" class="svg-ptot" />
          <circle v-if="sim.stable" :cx="paX(sim.deltaDeg)" :cy="paY(pOut)" r="5" class="svg-op" />
          <text x="34" :y="paY(1.0) + 3" class="svg-tick" text-anchor="end">1.0</text>
          <text x="34" :y="paY(2.0) + 3" class="svg-tick" text-anchor="end">2.0</text>
          <text :x="paX(90)" :y="RH - 10" class="svg-tick" text-anchor="middle">90°</text>
          <text :x="paX(180)" :y="RH - 10" class="svg-tick" text-anchor="end">180° (δ)</text>
          <text :x="RW - 18" y="26" class="svg-lbl-e0" text-anchor="end">P_max={{ sim.pMax.toFixed(2) }} @ {{ sim.dMaxDeg.toFixed(1) }}°</text>
        </svg>

        <svg v-else :viewBox="`0 0 ${RW} ${RH}`" class="em-svg">
          <line x1="42" :y1="RH - 28" :x2="RW - 14" :y2="RH - 28" class="svg-ax" />
          <line x1="42" y1="16" x2="42" :y2="RH - 28" class="svg-ax" />
          <path :d="vcPath(sim.vLow)" fill="none" class="svg-vc-ref" />
          <path :d="vcPath(sim.vHi)" fill="none" class="svg-vc-ref" />
          <path :d="vcPath(sim.vMain)" fill="none" class="svg-ptot" />
          <circle v-if="sim.stable" :cx="vcX(emfE0)" :cy="vcY(sim.Ia)" r="5" class="svg-op" />
          <text x="36" :y="vcY(1.0) + 3" class="svg-tick" text-anchor="end">1.0</text>
          <text x="36" :y="vcY(0) + 3" class="svg-tick" text-anchor="end">0</text>
          <text :x="vcX(1.0)" :y="RH - 10" class="svg-tick" text-anchor="middle">1.0</text>
          <text :x="vcX(1.8)" :y="RH - 10" class="svg-tick" text-anchor="middle">1.8 (E₀)</text>
          <text :x="RW - 16" y="26" class="svg-tick" text-anchor="end">Minimum = unity PF (cosφ = 1)</text>
        </svg>
      </div>
    </div>

    <div class="em-metrics">
      <div class="em-metric">
        <span>Power Angle δ / Limit δ<sub>max</sub></span>
        <strong>{{ sim.stable ? sim.deltaDeg.toFixed(1) + "°" : "Unstable" }} / {{ sim.dMaxDeg.toFixed(1) }}°</strong>
      </div>
      <div class="em-metric">
        <span>Reactive Power Q (&gt;0 supplying)</span>
        <strong>{{ sim.stable ? (sim.Q >= 0 ? "+" : "") + sim.Q.toFixed(3) + " pu" : "—" }}</strong>
      </div>
      <div class="em-metric">
        <span>Armature Current I<sub>A</sub> (I<sub>d</sub> / I<sub>q</sub>)</span>
        <strong>{{ sim.stable ? `${sim.Ia.toFixed(2)} (${sim.Id.toFixed(2)}/${sim.Iq.toFixed(2)})` : "—" }}</strong>
      </div>
      <div class="em-metric">
        <span>Power Factor cos φ</span>
        <strong>{{ sim.stable ? `${sim.pf.toFixed(3)} ${sim.Q >= 0 ? "lag" : "lead"}` : "—" }}</strong>
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

  &.is-active,
  &:hover {
    border-color: var(--vp-c-accent);
    background: var(--vp-c-accent-soft);
    color: var(--vp-c-accent);
    font-weight: 600;
  }
}

.em-controls-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem 1.1rem;
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
  grid-template-columns: 0.9fr 1.1fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.em-panel {
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.em-panel-head-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.28rem;
}

.em-panel-label {
  color: var(--vp-c-text-mute);
  font-size: 0.74rem;
  font-weight: 600;
}

.em-mini-tabs {
  display: inline-flex;
  gap: 0.25rem;
}

.em-mini {
  padding: 0.12rem 0.45rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg-alt);
  color: var(--vp-c-text-mute);
  font-size: 0.72rem;
  cursor: pointer;

  &.is-active {
    border-color: var(--vp-c-accent);
    color: var(--vp-c-accent);
    font-weight: 600;
  }
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

.svg-guide {
  stroke: var(--vp-c-border);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-v {
  stroke: var(--ink);
  stroke-width: 2.4;
}

.svg-v-dot {
  fill: var(--ink);
}

.svg-e0,
.svg-ptot {
  stroke: var(--vp-c-accent);
  stroke-width: 2.3;
}

.svg-e0-dot,
.svg-op {
  fill: var(--vp-c-accent);
  stroke: var(--vp-c-bg);
  stroke-width: 1.5;
}

.svg-ia {
  stroke: #1e7a56;
  stroke-width: 2.2;
}

.svg-ia-dot {
  fill: #1e7a56;
}

.svg-drop-q {
  stroke: #c27803;
  stroke-width: 1.6;
  stroke-dasharray: 4 3;
}

.svg-drop-d {
  stroke: #c83e37;
  stroke-width: 1.6;
  stroke-dasharray: 4 3;
}

.svg-pm {
  stroke: #c83e37;
  stroke-width: 1.4;
  stroke-dasharray: 4 3;
}

.svg-pfld {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.3;
  stroke-dasharray: 4 3;
}

.svg-prel {
  stroke: #1e7a56;
  stroke-width: 1.5;
  stroke-dasharray: 2 3;
}

.svg-vc-ref {
  stroke: var(--vp-c-border);
  stroke-width: 1.3;
  stroke-dasharray: 4 3;
}

.svg-lbl-v {
  fill: var(--ink);
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 700;
}

.svg-lbl-e0 {
  fill: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 9.8px;
  font-weight: 700;
}

.svg-lbl-ia {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 700;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
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
    font-size: 0.79rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .em-controls-2,
  .em-grid {
    grid-template-columns: 1fr;
  }

  .em-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
