<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";

const tab = ref<"rmf" | "winding">("rmf");

// Tab 1: RMF
const angleDeg = ref(45);
const seqPos = ref(true); // true: A-B-C (CCW), false: A-C-B (CW)
const playing = ref(false);
let rafId: number | null = null;
let lastTs = 0;

const stopAnim = (): void => {
  playing.value = false;
  if (rafId !== null && typeof cancelAnimationFrame !== "undefined") {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
};

const togglePlay = (): void => {
  if (playing.value) {
    stopAnim();
    return;
  }
  playing.value = true;
  lastTs = 0;
  const tick = (ts: number) => {
    if (!playing.value) return;
    if (lastTs > 0) {
      const dt = Math.min(0.05, (ts - lastTs) / 1000);
      angleDeg.value = (angleDeg.value + dt * 75) % 360;
    }
    lastTs = ts;
    rafId = requestAnimationFrame(tick);
  };
  rafId = requestAnimationFrame(tick);
};

onUnmounted(stopAnim);

const rmf = computed(() => {
  const wt = (angleDeg.value * Math.PI) / 180;
  const shiftB = seqPos.value ? (-2 * Math.PI) / 3 : (2 * Math.PI) / 3;
  const shiftC = seqPos.value ? (-4 * Math.PI) / 3 : (4 * Math.PI) / 3;

  const ia = Math.cos(wt);
  const ib = Math.cos(wt + shiftB);
  const ic = Math.cos(wt + shiftC);

  // Stator physical winding magnetic axes at 0°, 120°, 240°
  const axA = 0;
  const axB = (2 * Math.PI) / 3;
  const axC = (4 * Math.PI) / 3;

  const vec = (mag: number, axis: number) => ({ x: mag * Math.cos(axis), y: mag * Math.sin(axis) });
  const ba = vec(ia, axA);
  const bb = vec(ib, axB);
  const bc = vec(ic, axC);
  const bNet = { x: ba.x + bb.x + bc.x, y: ba.y + bb.y + bc.y };
  const bMag = Math.hypot(bNet.x, bNet.y);
  let bAngDeg = (Math.atan2(bNet.y, bNet.x) * 180) / Math.PI;
  if (bAngDeg < 0) bAngDeg += 360;

  return { ia, ib, ic, ba, bb, bc, bNet, bMag, bAngDeg };
});

// RMF SVG coordinates
const RC = 115;
const RScale = 55;
const rx = (v: number): number => RC + v * RScale;
const ry = (v: number): number => RC - v * RScale;

// 3-phase current curves SVG
const WW = 330;
const WH = 230;
const wx = (deg: number): number => 34 + (deg / 360) * (WW - 48);
const wy = (val: number): number => WH / 2 - val * 74;

const wavePath = (phaseOffsetDeg: number): string => {
  const pts: string[] = [];
  for (let d = 0; d <= 360; d += 4) {
    const v = Math.cos(((d + phaseOffsetDeg) * Math.PI) / 180);
    pts.push(`${d === 0 ? "M" : "L"}${wx(d).toFixed(1)},${wy(v).toFixed(1)}`);
  }
  return pts.join(" ");
};

const pathIa = computed(() => wavePath(0));
const pathIb = computed(() => wavePath(seqPos.value ? -120 : 120));
const pathIc = computed(() => wavePath(seqPos.value ? -240 : 240));

// Tab 2: Winding factor k_d, k_p, k_w
const qSlots = ref(3); // slots per pole per phase
const pitchY = ref(0.8333); // y = 5/6 default

const windingData = computed(() => {
  const q = qSlots.value;
  const y = pitchY.value;
  const alphaDegVal = 60 / q;
  const alphaRad = (alphaDegVal * Math.PI) / 180;
  const harms = [1, 3, 5, 7, 11, 13];
  const rows = harms.map((nu) => {
    const den = q * Math.sin((nu * alphaRad) / 2);
    const kd = Math.abs(den) < 1e-9 ? 1 : Math.sin((q * nu * alphaRad) / 2) / den;
    const kp = Math.sin((nu * y * Math.PI) / 2);
    const kw = kd * kp;
    return { nu, kd: Math.abs(kd), kp: Math.abs(kp), kw: Math.abs(kw) };
  });
  return { alphaDegVal, rows };
});
</script>

<template>
  <div class="em-lab">
    <div class="em-head">
      <div>
        <span class="em-badge">INTERACTIVE LAB</span>
        <h4 class="em-title">3-Phase Rotating Magnetic Field (RMF) &amp; Winding Factors (k<sub>d</sub>, k<sub>p</sub>, k<sub>w</sub>)</h4>
      </div>
      <div class="em-tabs">
        <button type="button" class="em-chip" :class="{ 'is-active': tab === 'rmf' }" @click="tab = 'rmf'">
          Rotating Field (RMF)
        </button>
        <button type="button" class="em-chip" :class="{ 'is-active': tab === 'winding' }" @click="stopAnim(); tab = 'winding'">
          Winding Factors &amp; Harmonics
        </button>
      </div>
    </div>

    <!-- TAB 1: RMF -->
    <template v-if="tab === 'rmf'">
      <div class="em-presets">
        <button type="button" class="em-chip is-accent" @click="togglePlay">
          {{ playing ? "⏸ Pause" : "▶ Play Rotation" }}
        </button>
        <button type="button" class="em-chip" :class="{ 'is-active': seqPos }" @click="seqPos = true">
          Positive Sequence A–B–C (CCW)
        </button>
        <button type="button" class="em-chip" :class="{ 'is-active': !seqPos }" @click="seqPos = false">
          Negative Sequence A–C–B (CW Reverse)
        </button>
      </div>

      <label class="em-slider">
        <span class="em-slider-row">
          <span>Electrical Angle ωt</span>
          <strong>{{ angleDeg.toFixed(0) }}° (Net Field ∠B<sub>net</sub> = {{ rmf.bAngDeg.toFixed(0) }}°, Constant |B<sub>net</sub>| = 1.50 B<sub>m</sub>)</strong>
        </span>
        <input v-model.number="angleDeg" type="range" min="0" max="360" step="1" />
      </label>

      <div class="em-grid">
        <!-- Stator Vector Circle -->
        <div class="em-panel">
          <div class="em-panel-label">Pulsating Phase MMFs Combine into Constant-Amplitude Rotating B<sub>net</sub></div>
          <svg viewBox="0 0 230 230" class="em-svg">
            <!-- Stator ring & 1.5 Bm locus -->
            <circle :cx="RC" :cy="RC" :r="1.5 * RScale" class="svg-locus" fill="none" />
            <circle :cx="RC" :cy="RC" :r="1.0 * RScale" class="svg-inner" fill="none" />
            <!-- Axes at 0, 120, 240 -->
            <line :x1="rx(-1.6)" :y1="ry(0)" :x2="rx(1.6)" :y2="ry(0)" class="svg-ax" />
            <line :x1="rx(-1.6 * Math.cos(2.0944))" :y1="ry(-1.6 * Math.sin(2.0944))" :x2="rx(1.6 * Math.cos(2.0944))" :y2="ry(1.6 * Math.sin(2.0944))" class="svg-ax" />
            <line :x1="rx(-1.6 * Math.cos(4.1888))" :y1="ry(-1.6 * Math.sin(4.1888))" :x2="rx(1.6 * Math.cos(4.1888))" :y2="ry(1.6 * Math.sin(4.1888))" class="svg-ax" />

            <text :x="rx(1.66)" :y="ry(0) + 4" class="svg-lbl-a">A</text>
            <text :x="rx(1.68 * Math.cos(2.0944))" :y="ry(1.68 * Math.sin(2.0944))" class="svg-lbl-b" text-anchor="middle">B</text>
            <text :x="rx(1.68 * Math.cos(4.1888))" :y="ry(1.68 * Math.sin(4.1888)) + 8" class="svg-lbl-c" text-anchor="middle">C</text>

            <!-- Phase pulsing vectors -->
            <line :x1="RC" :y1="RC" :x2="rx(rmf.ba.x)" :y2="ry(rmf.ba.y)" class="svg-va" />
            <line :x1="RC" :y1="RC" :x2="rx(rmf.bb.x)" :y2="ry(rmf.bb.y)" class="svg-vb" />
            <line :x1="RC" :y1="RC" :x2="rx(rmf.bc.x)" :y2="ry(rmf.bc.y)" class="svg-vc" />

            <!-- Resultant rotating vector -->
            <line :x1="RC" :y1="RC" :x2="rx(rmf.bNet.x)" :y2="ry(rmf.bNet.y)" class="svg-vnet" />
            <circle :cx="rx(rmf.bNet.x)" :cy="ry(rmf.bNet.y)" r="5" class="svg-net-tip" />
          </svg>
        </div>

        <!-- 3-phase waveforms -->
        <div class="em-panel">
          <div class="em-panel-label">3-Phase Stator Currents i<sub>a</sub>, i<sub>b</sub>, i<sub>c</sub> (vertical line = current ωt)</div>
          <svg :viewBox="`0 0 ${WW} ${WH}`" class="em-svg">
            <line x1="34" :y1="wy(0)" :x2="WW - 14" :y2="wy(0)" class="svg-ax" />
            <line x1="34" y1="18" x2="34" :y2="WH - 24" class="svg-ax" />
            <path :d="pathIa" fill="none" class="svg-wa" />
            <path :d="pathIb" fill="none" class="svg-wb" />
            <path :d="pathIc" fill="none" class="svg-wc" />
            <line :x1="wx(angleDeg)" y1="18" :x2="wx(angleDeg)" :y2="WH - 24" class="svg-cursor" />
            <circle :cx="wx(angleDeg)" :cy="wy(rmf.ia)" r="4" class="svg-da" />
            <circle :cx="wx(angleDeg)" :cy="wy(rmf.ib)" r="4" class="svg-db" />
            <circle :cx="wx(angleDeg)" :cy="wy(rmf.ic)" r="4" class="svg-dc" />
            <text x="28" :y="wy(1) + 4" class="svg-tick" text-anchor="end">+I_m</text>
            <text x="28" :y="wy(0) + 4" class="svg-tick" text-anchor="end">0</text>
            <text x="28" :y="wy(-1) + 4" class="svg-tick" text-anchor="end">−I_m</text>
            <text v-for="d in [0, 120, 240, 360]" :key="d" :x="wx(d)" :y="WH - 8" class="svg-tick" text-anchor="middle">{{ d }}°</text>
          </svg>
        </div>
      </div>

      <div class="em-metrics">
        <div class="em-metric"><span>i<sub>a</sub> / I<sub>m</sub></span><strong>{{ rmf.ia.toFixed(2) }}</strong></div>
        <div class="em-metric"><span>i<sub>b</sub> / I<sub>m</sub></span><strong>{{ rmf.ib.toFixed(2) }}</strong></div>
        <div class="em-metric"><span>i<sub>c</sub> / I<sub>m</sub></span><strong>{{ rmf.ic.toFixed(2) }}</strong></div>
        <div class="em-metric"><span>Net Field |B<sub>net</sub>| / B<sub>m</sub></span><strong>{{ rmf.bMag.toFixed(2) }} (Constant)</strong></div>
      </div>
    </template>

    <!-- TAB 2: WINDING FACTOR -->
    <template v-else>
      <div class="em-presets">
        <button type="button" class="em-chip" @click="qSlots = 1; pitchY = 1.0">Concentrated Full-Pitch (q=1, y=1)</button>
        <button type="button" class="em-chip" @click="qSlots = 3; pitchY = 0.8333">Short-Pitch y = 5/6 (Suppresses 5th &amp; 7th)</button>
        <button type="button" class="em-chip" @click="qSlots = 3; pitchY = 0.8">Eliminate 5th (y = 4/5)</button>
        <button type="button" class="em-chip" @click="qSlots = 3; pitchY = 0.6667">Eliminate 3rd (y = 2/3)</button>
      </div>

      <div class="em-controls-2">
        <label class="em-slider">
          <span class="em-slider-row">
            <span>Slots per Pole per Phase q (slot angle α = {{ windingData.alphaDegVal.toFixed(1) }}°)</span>
            <strong>q = {{ qSlots }}</strong>
          </span>
          <input v-model.number="qSlots" type="range" min="1" max="6" step="1" />
        </label>

        <label class="em-slider">
          <span class="em-slider-row">
            <span>Coil Pitch Ratio y = Coil Span / Pole Pitch</span>
            <strong>y = {{ pitchY.toFixed(3) }}</strong>
          </span>
          <input v-model.number="pitchY" type="range" min="0.5" max="1.0" step="0.0167" />
        </label>
      </div>

      <div class="em-panel">
        <div class="em-panel-label">Harmonic Winding Factors (light blue: |k<sub>dν</sub>|, green: |k<sub>pν</sub>|, dark blue: |k<sub>wν</sub>| = |k<sub>dν</sub>k<sub>pν</sub>|)</div>
        <svg viewBox="0 0 600 190" class="em-svg">
          <line x1="38" y1="158" x2="585" y2="158" class="svg-ax" />
          <line x1="38" y1="16" x2="38" y2="158" class="svg-ax" />
          <line x1="38" y1="28" x2="585" y2="28" class="svg-inner" />
          <text x="32" y="32" class="svg-tick" text-anchor="end">1.0</text>
          <text x="32" y="95" class="svg-tick" text-anchor="end">0.5</text>
          <text x="32" y="161" class="svg-tick" text-anchor="end">0</text>

          <g v-for="(row, idx) in windingData.rows" :key="row.nu" :transform="`translate(${60 + idx * 88}, 0)`">
            <rect x="0" :y="158 - row.kd * 130" width="16" :height="Math.max(1.5, row.kd * 130)" class="bar-kd" rx="1" />
            <rect x="20" :y="158 - row.kp * 130" width="16" :height="Math.max(1.5, row.kp * 130)" class="bar-kp" rx="1" />
            <rect x="40" :y="158 - row.kw * 130" width="16" :height="Math.max(1.5, row.kw * 130)" class="bar-kw" rx="1" />
            <text x="28" y="175" class="svg-tick" text-anchor="middle">ν = {{ row.nu }}</text>
            <text x="48" :y="153 - row.kw * 130" class="bar-lbl" text-anchor="middle">{{ row.kw.toFixed(2) }}</text>
          </g>
        </svg>
      </div>

      <div class="em-metrics">
        <div class="em-metric"><span>Fundamental k<sub>d1</sub> / k<sub>p1</sub></span><strong>{{ windingData.rows[0].kd.toFixed(3) }} / {{ windingData.rows[0].kp.toFixed(3) }}</strong></div>
        <div class="em-metric"><span>Fundamental k<sub>w1</sub></span><strong>{{ windingData.rows[0].kw.toFixed(3) }}</strong></div>
        <div class="em-metric"><span>5th Harmonic |k<sub>w5</sub>|</span><strong>{{ windingData.rows[2].kw.toFixed(3) }}</strong></div>
        <div class="em-metric"><span>7th Harmonic |k<sub>w7</sub>|</span><strong>{{ windingData.rows[3].kw.toFixed(3) }}</strong></div>
      </div>
    </template>
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

.em-tabs,
.em-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
}

.em-presets {
  margin-bottom: 0.75rem;
}

.em-chip {
  padding: 0.24rem 0.6rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);
  color: var(--vp-c-text);
  font-size: 0.79rem;
  cursor: pointer;

  &.is-active,
  &.is-accent,
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
  margin-bottom: 0.8rem;
}

.em-slider {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-bottom: 0.75rem;
}

.em-slider-row {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
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
  grid-template-columns: 0.85fr 1.15fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.em-panel {
  margin-bottom: 0.75rem;
  padding: 0.58rem 0.68rem;
  border: 1px solid var(--vp-c-border);
  border-radius: var(--r, 2px);
  background: var(--vp-c-bg);

  .em-grid & {
    margin-bottom: 0;
  }
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

.svg-inner {
  stroke: var(--vp-c-border);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-locus {
  stroke: var(--vp-c-accent);
  stroke-width: 1.2;
  stroke-dasharray: 4 3;
  opacity: 0.55;
}

.svg-va,
.svg-wa {
  stroke: #c83e37;
  stroke-width: 2;
}

.svg-vb,
.svg-wb {
  stroke: #1e7a56;
  stroke-width: 2;
}

.svg-vc,
.svg-wc {
  stroke: #c27803;
  stroke-width: 2;
}

.svg-vnet {
  stroke: var(--vp-c-accent);
  stroke-width: 3.2;
  stroke-linecap: round;
}

.svg-net-tip {
  fill: var(--vp-c-accent);
}

.svg-cursor {
  stroke: var(--ink);
  stroke-width: 1.3;
  stroke-dasharray: 3 3;
}

.svg-da {
  fill: #c83e37;
}

.svg-db {
  fill: #1e7a56;
}

.svg-dc {
  fill: #c27803;
}

.svg-lbl-a {
  fill: #c83e37;
  font-family: var(--vp-font-mono);
  font-size: 11px;
  font-weight: 700;
}

.svg-lbl-b {
  fill: #1e7a56;
  font-family: var(--vp-font-mono);
  font-size: 11px;
  font-weight: 700;
}

.svg-lbl-c {
  fill: #c27803;
  font-family: var(--vp-font-mono);
  font-size: 11px;
  font-weight: 700;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9.5px;
}

.bar-kd {
  fill: var(--vp-c-accent);
  opacity: 0.42;
}

.bar-kp {
  fill: #1e7a56;
  opacity: 0.72;
}

.bar-kw {
  fill: var(--vp-c-accent);
}

.bar-lbl {
  fill: var(--ink);
  font-family: var(--vp-font-mono);
  font-size: 9px;
  font-weight: 600;
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
    font-size: 0.81rem;
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
