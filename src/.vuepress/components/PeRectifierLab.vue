<script setup lang="ts">
import { computed, ref } from "vue";

const props = withDefaults(
  defineProps<{
    phaseControlled?: boolean;
    defaultTopology?: "1ph" | "3ph";
    defaultAlpha?: number;
    defaultX?: number;
  }>(),
  {
    phaseControlled: true,
    defaultTopology: "1ph",
    defaultAlpha: 35,
    defaultX: 0.12,
  }
);

const topology = ref<"1ph" | "3ph">(props.defaultTopology);
const alphaDeg = ref(props.phaseControlled ? props.defaultAlpha : 0);
const xComm = ref(props.defaultX); // normalized 2*w*Ls*Id / Vmax

const applyPreset = (topo: "1ph" | "3ph", a: number, x: number): void => {
  topology.value = topo;
  alphaDeg.value = props.phaseControlled ? a : 0;
  xComm.value = x;
};

const sim = computed(() => {
  const is3ph = topology.value === "3ph";
  const alpha = ((props.phaseControlled ? alphaDeg.value : 0) * Math.PI) / 180;
  const x = xComm.value;

  const cosAU = Math.cos(alpha) - x;
  const commFailure = cosAU <= -0.996;
  const uRad = commFailure ? Math.max(0, Math.PI - alpha) : Math.max(0, Math.acos(Math.max(-1, Math.min(1, cosAU))) - alpha);
  const uDeg = (uRad * 180) / Math.PI;
  const gammaDeg = 180 - (alpha * 180) / Math.PI - uDeg;
  const isInverter = alpha > Math.PI / 2 + 1e-6;
  const marginWarn = props.phaseControlled && (commFailure || (isInverter && gammaDeg < 5));

  // Sample 720 points over [0, 2*pi]
  const M = 720;
  const thetas: number[] = [];
  const vsArr: number[] = [];
  const vdArr: number[] = [];
  const isArr: number[] = [];
  const inOverlap: boolean[] = [];

  // Helper for 3-phase line-to-line voltages (peak = 1)
  // v_ab = sin(th + 30°), v_ac = sin(th - 30°), v_bc = sin(th - 90°),
  // v_ba = sin(th - 150°), v_ca = sin(th - 210°), v_cb = sin(th - 270°)
  const vll = (k: number, th: number): number => Math.sin(th + Math.PI / 6 - (k * Math.PI) / 3);

  for (let i = 0; i <= M; i++) {
    const th = (2 * Math.PI * i) / M;
    thetas.push(th);

    if (!is3ph) {
      const vs = Math.sin(th);
      vsArr.push(vs);

      // Position relative to alpha modulo pi
      const rel = ((th - alpha) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI);
      let vd = 0;
      let isVal = 0;
      let ov = false;

      if (rel < uRad) {
        ov = true;
        vd = 0;
        isVal = x > 1e-6 ? -1 + (2 / x) * (Math.cos(alpha) - Math.cos(alpha + rel)) : 1;
      } else if (rel < Math.PI) {
        vd = Math.sin(alpha + rel);
        isVal = 1;
      } else if (rel < Math.PI + uRad) {
        ov = true;
        vd = 0;
        const r2 = rel - Math.PI;
        isVal = x > 1e-6 ? 1 - (2 / x) * (Math.cos(alpha) - Math.cos(alpha + r2)) : -1;
      } else {
        vd = -Math.sin(alpha + rel);
        isVal = -1;
      }
      vdArr.push(vd);
      isArr.push(isVal);
      inOverlap.push(ov);
    } else {
      // Phase-A voltage scaled for reference overlay (peak = 1/sqrt(3) -> normalize to 1 for display or show v_a*sqrt(3))
      const va = Math.sin(th);
      vsArr.push(va);

      // Natural commutation points at 30° + 60°*k; shifted by alpha
      const shift = th - Math.PI / 6 - alpha;
      const wrapped = ((shift % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
      const seg = Math.floor(wrapped / (Math.PI / 3)) % 6;
      const loc = wrapped - seg * (Math.PI / 3);
      let vd = 0;
      let ov = false;

      if (loc < uRad && uRad > 1e-6) {
        ov = true;
        const prevSeg = (seg + 5) % 6;
        vd = 0.5 * (vll(prevSeg, th) + vll(seg, th));
      } else {
        vd = vll(seg, th);
      }
      vdArr.push(vd);
      inOverlap.push(ov);

      // Phase-A line current:
      // Positive pulse starts at seg=0 (30°+alpha), ends at seg=2 (150°+alpha)
      // Negative pulse starts at seg=3 (210°+alpha), ends at seg=5 (330°+alpha)
      const ramp = (localAngle: number): number =>
        x > 1e-6 ? Math.min(1, Math.max(0, (Math.cos(alpha) - Math.cos(alpha + localAngle)) / x)) : 1;

      let ia = 0;
      if (seg === 0) {
        ia = loc < uRad ? ramp(loc) : 1;
      } else if (seg === 1) {
        ia = 1;
      } else if (seg === 2) {
        ia = loc < uRad ? 1 - ramp(loc) : 0;
      } else if (seg === 3) {
        ia = loc < uRad ? -ramp(loc) : -1;
      } else if (seg === 4) {
        ia = -1;
      } else {
        ia = loc < uRad ? -(1 - ramp(loc)) : 0;
      }
      isArr.push(ia);
    }
  }

  // Exact numerical Fourier analysis of isArr (excluding duplicate endpoint M)
  let sumSq = 0;
  let vdMean = 0;
  for (let i = 0; i < M; i++) {
    sumSq += isArr[i] * isArr[i];
    vdMean += vdArr[i];
  }
  const isRms = Math.sqrt(sumSq / M);
  vdMean /= M;

  const harmonics: { h: number; rms: number; rel: number }[] = [];
  let a1 = 0;
  let b1 = 0;
  for (let h = 1; h <= 13; h += 2) {
    let ah = 0;
    let bh = 0;
    for (let i = 0; i < M; i++) {
      const th = thetas[i];
      ah += isArr[i] * Math.sin(h * th);
      bh += isArr[i] * Math.cos(h * th);
    }
    ah = (2 / M) * ah;
    bh = (2 / M) * bh;
    const peak = Math.hypot(ah, bh);
    const rms = peak / Math.SQRT2;
    if (h === 1) {
      a1 = ah;
      b1 = bh;
    }
    harmonics.push({ h, rms, rel: 0 });
  }
  const i1Rms = harmonics[0].rms || 1e-9;
  for (const item of harmonics) item.rel = item.rms / i1Rms;

  // Fundamental phase lag relative to sin(th):
  // i_s1(th) = a1 sin(th) + b1 cos(th) = I1_pk * sin(th - phi1), where phi1 = atan2(-b1, a1)
  const phi1Rad = Math.atan2(-b1, a1);
  const phi1Deg = (phi1Rad * 180) / Math.PI;
  const dpf = Math.cos(phi1Rad);
  const xi1 = isRms > 1e-6 ? i1Rms / isRms : 0;
  const pf = xi1 * dpf;
  const thd = xi1 > 1e-6 ? Math.sqrt(Math.max(0, 1 / (xi1 * xi1) - 1)) * 100 : 0;
  const vdIdeal0 = is3ph ? 3 / Math.PI : 2 / Math.PI;
  const vdRatio = vdMean / vdIdeal0;

  // Fundamental waveform i_s1(th)
  const is1Arr = thetas.map((th) => a1 * Math.sin(th) + b1 * Math.cos(th));

  return {
    thetas,
    vsArr,
    vdArr,
    isArr,
    is1Arr,
    inOverlap,
    uDeg,
    gammaDeg,
    isInverter,
    commFailure,
    marginWarn,
    vdRatio,
    vdMean,
    xi1,
    dpf,
    pf,
    phi1Deg,
    thd,
    harmonics,
  };
});

// SVG layout helpers
const W1 = 640;
const H1 = 172;
const padL = 42;
const padR = 16;
const padT = 14;
const padB = 22;

const x1 = (th: number): number => padL + (th / (2 * Math.PI)) * (W1 - padL - padR);
const y1 = (v: number): number => padT + ((1.15 - v) / 2.3) * (H1 - padT - padB);

const toPath = (arr: number[], xFn: (t: number) => number, yFn: (v: number) => number): string => {
  const ts = sim.value.thetas;
  const pts: string[] = [];
  for (let i = 0; i < ts.length; i += 2) {
    pts.push(`${i === 0 ? "M" : "L"}${xFn(ts[i]).toFixed(1)},${yFn(arr[i]).toFixed(1)}`);
  }
  return pts.join(" ");
};

const vsPath = computed(() => toPath(sim.value.vsArr, x1, y1));
const vdPath = computed(() => toPath(sim.value.vdArr, x1, y1));

// Bottom left current chart
const W2 = 380;
const H2 = 162;
const x2 = (th: number): number => 36 + (th / (2 * Math.PI)) * (W2 - 48);
const y2 = (v: number): number => 14 + ((1.35 - v) / 2.7) * (H2 - 36);
const isPath = computed(() => toPath(sim.value.isArr, x2, y2));
const is1Path = computed(() => toPath(sim.value.is1Arr, x2, y2));

// Bottom right harmonic spectrum chart
const W3 = 250;
const H3 = 162;
const barX = (idx: number): number => 32 + idx * 29;
const barH = (rel: number): number => Math.min(1, rel) * 110;

const modeBadge = computed(() => {
  if (sim.value.commFailure) return { text: "Commutation Failure!", cls: "is-bad" };
  if (sim.value.marginWarn) return { text: `Low Margin γ = ${sim.value.gammaDeg.toFixed(1)}° (< 5°)`, cls: "is-bad" };
  if (!props.phaseControlled) return { text: "Diode Rectifier (α = 0°)", cls: "is-ok" };
  if (sim.value.isInverter) return { text: "Inverter Mode (Vd < 0)", cls: "is-warn" };
  return { text: "Rectifier Mode (Vd > 0)", cls: "is-ok" };
});
</script>

<template>
  <div class="pe-lab">
    <div class="pe-head">
      <div>
        <span class="pe-badge">INTERACTIVE LAB</span>
        <h4 class="pe-title">
          {{ phaseControlled ? "Phase-Controlled Rectifier / Inverter & Commutation Overlap" : "Diode Bridge Waveforms, Harmonics & Commutation Overlap" }}
        </h4>
      </div>
      <span class="pe-status" :class="modeBadge.cls">{{ modeBadge.text }}</span>
    </div>

    <div class="pe-presets">
      <button type="button" class="pe-chip" :class="{ 'is-active': topology === '1ph' }" @click="topology = '1ph'">
        1-Phase Bridge
      </button>
      <button type="button" class="pe-chip" :class="{ 'is-active': topology === '3ph' }" @click="topology = '3ph'">
        3-Phase 6-Pulse Bridge
      </button>
      <template v-if="phaseControlled">
        <button type="button" class="pe-chip" @click="applyPreset('1ph', 0, 0.15)">α = 0° (Diode Equiv.)</button>
        <button type="button" class="pe-chip" @click="applyPreset('1ph', 60, 0.12)">Deep Delay α = 60° (Low PF)</button>
        <button type="button" class="pe-chip" @click="applyPreset('1ph', 135, 0.18)">Inverter Mode α = 135°</button>
        <button type="button" class="pe-chip" @click="applyPreset('3ph', 150, 0.25)">Inverter Limit (Near Failure)</button>
      </template>
      <template v-else>
        <button type="button" class="pe-chip" @click="applyPreset('1ph', 0, 0)">1-Ph Ideal (Ls = 0)</button>
        <button type="button" class="pe-chip" @click="applyPreset('1ph', 0, 0.25)">1-Ph Overlap (Ls &gt; 0)</button>
        <button type="button" class="pe-chip" @click="applyPreset('3ph', 0, 0)">3-Ph Ideal (6k±1 Harmonics)</button>
        <button type="button" class="pe-chip" @click="applyPreset('3ph', 0, 0.25)">3-Ph Voltage Notches (Ls &gt; 0)</button>
      </template>
    </div>

    <div class="pe-controls">
      <label v-if="phaseControlled" class="pe-slider">
        <span class="pe-slider-row">
          <span>Firing Delay Angle α</span>
          <strong>{{ alphaDeg }}°</strong>
        </span>
        <input v-model.number="alphaDeg" type="range" min="0" max="172" step="1" />
      </label>

      <label class="pe-slider">
        <span class="pe-slider-row">
          <span>AC Inductance Commutation Factor 2ωL<sub>s</sub>I<sub>d</sub> / V<sub>max</sub></span>
          <strong>{{ xComm.toFixed(2) }} (Overlap u = {{ sim.uDeg.toFixed(1) }}°)</strong>
        </span>
        <input v-model.number="xComm" type="range" min="0" max="0.55" step="0.01" />
      </label>
    </div>

    <!-- Top waveform: vd and vs -->
    <div class="pe-panel">
      <div class="pe-panel-label">
        DC Output Voltage v<sub>d</sub>(ωt) (solid, average V<sub>d</sub> dashed) &amp; AC Reference (gray)
      </div>
      <svg :viewBox="`0 0 ${W1} ${H1}`" class="pe-svg">
        <line :x1="padL" :y1="y1(0)" :x2="W1 - padR" :y2="y1(0)" class="svg-axis" />
        <line :x1="padL" :y1="padT" :x2="padL" :y2="H1 - padB" class="svg-axis" />
        <line :x1="padL" :y1="y1(sim.vdMean)" :x2="W1 - padR" :y2="y1(sim.vdMean)" class="svg-avg" />
        <path :d="vsPath" fill="none" class="svg-ref-wave" />
        <path :d="vdPath" fill="none" class="svg-vd" />
        <text :x="padL - 5" :y="y1(1) + 3" class="svg-tick" text-anchor="end">+1</text>
        <text :x="padL - 5" :y="y1(0) + 3" class="svg-tick" text-anchor="end">0</text>
        <text :x="padL - 5" :y="y1(-1) + 3" class="svg-tick" text-anchor="end">−1</text>
        <text v-for="deg in [0, 90, 180, 270, 360]" :key="deg" :x="x1((deg * Math.PI) / 180)" :y="H1 - 6" class="svg-tick" text-anchor="middle">
          {{ deg }}°
        </text>
        <text :x="W1 - padR - 4" :y="Math.max(22, Math.min(H1 - 28, y1(sim.vdMean) - 5))" class="svg-avg-lbl" text-anchor="end">
          V_d = {{ sim.vdMean.toFixed(2) }} V_max
        </text>
      </svg>
    </div>

    <div class="pe-bottom-grid">
      <!-- AC current & fundamental -->
      <div class="pe-panel">
        <div class="pe-panel-label">AC Line Current i<sub>s</sub>(ωt) (solid) &amp; Fundamental i<sub>s1</sub>(ωt) (dashed)</div>
        <svg :viewBox="`0 0 ${W2} ${H2}`" class="pe-svg">
          <line x1="36" :y1="y2(0)" :x2="W2 - 12" :y2="y2(0)" class="svg-axis" />
          <line x1="36" y1="12" x2="36" :y2="H2 - 22" class="svg-axis" />
          <path :d="is1Path" fill="none" class="svg-fund" />
          <path :d="isPath" fill="none" class="svg-is" />
          <text x="31" :y="y2(1) + 3" class="svg-tick" text-anchor="end">+I_d</text>
          <text x="31" :y="y2(0) + 3" class="svg-tick" text-anchor="end">0</text>
          <text x="31" :y="y2(-1) + 3" class="svg-tick" text-anchor="end">−I_d</text>
          <text v-for="deg in [0, 180, 360]" :key="'c' + deg" :x="x2((deg * Math.PI) / 180)" :y="H2 - 6" class="svg-tick" text-anchor="middle">
            {{ deg }}°
          </text>
        </svg>
      </div>

      <!-- Harmonic Spectrum -->
      <div class="pe-panel">
        <div class="pe-panel-label">Input Current Harmonic Spectrum I<sub>sh</sub> / I<sub>s1</sub></div>
        <svg :viewBox="`0 0 ${W3} ${H3}`" class="pe-svg">
          <line x1="24" :y1="H3 - 26" :x2="W3 - 10" :y2="H3 - 26" class="svg-axis" />
          <g v-for="(item, idx) in sim.harmonics" :key="item.h">
            <rect
              :x="barX(idx)"
              :y="H3 - 26 - barH(item.rel)"
              width="18"
              :height="Math.max(1.5, barH(item.rel))"
              :class="item.h === 1 ? 'svg-bar-1' : 'svg-bar-h'"
              rx="1"
            />
            <text :x="barX(idx) + 9" :y="H3 - 12" class="svg-tick" text-anchor="middle">h={{ item.h }}</text>
            <text
              v-if="item.rel > 0.03"
              :x="barX(idx) + 9"
              :y="H3 - 30 - barH(item.rel)"
              class="svg-bar-lbl"
              text-anchor="middle"
            >
              {{ Math.round(item.rel * 100) }}%
            </text>
          </g>
        </svg>
      </div>
    </div>

    <div class="pe-metrics">
      <div class="pe-metric">
        <span>V<sub>d</sub> / V<sub>d0</sub> (vs. Ideal No-Load)</span>
        <strong>{{ (sim.vdRatio * 100).toFixed(1) }}%</strong>
      </div>
      <div class="pe-metric">
        <span>Distortion Factor ξ<sub>1</sub> / THD</span>
        <strong>{{ sim.xi1.toFixed(3) }} / {{ sim.thd.toFixed(1) }}%</strong>
      </div>
      <div class="pe-metric">
        <span>Displacement PF cos φ<sub>1</sub> (φ<sub>1</sub>)</span>
        <strong>{{ sim.dpf.toFixed(3) }} ({{ sim.phi1Deg.toFixed(1) }}°)</strong>
      </div>
      <div class="pe-metric">
        <span>Total Power Factor PF = ξ<sub>1</sub>cosφ<sub>1</sub></span>
        <strong>{{ sim.pf.toFixed(3) }}</strong>
      </div>
      <div class="pe-metric">
        <span>Overlap u / Extinction γ</span>
        <strong>{{ sim.uDeg.toFixed(1) }}° / {{ sim.gammaDeg.toFixed(1) }}°</strong>
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
  font-size: 1.03rem;
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
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.7rem 1.15rem;
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
  gap: 0.5rem;
  font-size: 0.82rem;

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

.pe-panel {
  margin-bottom: 0.75rem;
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
}

.pe-panel-label {
  margin-bottom: 0.3rem;
  color: var(--vp-c-text-mute);
  font-size: 0.76rem;
  font-weight: 600;
}

.pe-bottom-grid {
  display: grid;
  grid-template-columns: 1.38fr 1fr;
  gap: 0.75rem;

  .pe-panel {
    margin-bottom: 0.75rem;
  }
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

.svg-ref-wave {
  stroke: var(--vp-c-border);
  stroke-width: 1.2;
  stroke-dasharray: 4 3;
}

.svg-vd {
  stroke: var(--vp-c-accent);
  stroke-width: 2.2;
  stroke-linejoin: round;
}

.svg-avg {
  stroke: #c83e37;
  stroke-width: 1.3;
  stroke-dasharray: 5 3;
}

.svg-avg-lbl {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 10px;
  font-weight: 600;
}

.svg-is {
  stroke: #1e7a56;
  stroke-width: 2.1;
  stroke-linejoin: round;
}

.svg-fund {
  stroke: #c27803;
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-bar-1 {
  fill: var(--vp-c-accent);
}

.svg-bar-h {
  fill: #c83e37;
  opacity: 0.78;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
}

.svg-bar-lbl {
  fill: var(--vp-c-text);
  font-family: var(--vp-font-mono);
  font-size: 8.5px;
}

.pe-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
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
    font-size: 0.81rem;
    font-variant-numeric: tabular-nums;
  }
}

@media (max-width: 719px) {
  .pe-bottom-grid {
    grid-template-columns: 1fr;
  }

  .pe-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
