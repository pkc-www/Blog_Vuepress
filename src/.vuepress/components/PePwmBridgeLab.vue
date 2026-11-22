<script setup lang="ts">
import { computed, ref } from "vue";

const mCtrl = ref(0.5); // v_control / V_tri_hat in [-0.92, 0.92]

// Symmetric triangle wave in [-1, 1] with period 1
const tri = (t: number): number => {
  const f = ((t % 1) + 1) % 1;
  return f < 0.5 ? -1 + 4 * f : 3 - 4 * f;
};

const sim = computed(() => {
  const m = mCtrl.value;
  const N = 400; // over 2 switching periods t in [0, 2]
  const dt = 2 / N;
  const ts: number[] = [];
  const vTri: number[] = [];
  const voBi: number[] = [];
  const voUni: number[] = [];

  for (let i = 0; i <= N; i++) {
    const t = i * dt;
    const tr = tri(t);
    ts.push(t);
    vTri.push(tr);

    const bi = m > tr ? 1 : -1;
    voBi.push(bi);

    const van = m > tr ? 1 : 0;
    const vbn = -m > tr ? 1 : 0;
    voUni.push(van - vbn);
  }

  // Integrate (vo - m) to obtain normalized inductor current ripple (zero mean)
  const integrateRipple = (arr: number[]): { curve: number[]; pp: number } => {
    const raw: number[] = [0];
    for (let i = 1; i < arr.length; i++) {
      raw.push(raw[i - 1] + 0.5 * (arr[i - 1] - m + (arr[i] - m)) * dt);
    }
    const mean = raw.reduce((a, b) => a + b, 0) / raw.length;
    const centered = raw.map((v) => v - mean);
    const pp = Math.max(...centered) - Math.min(...centered);
    return { curve: centered, pp };
  };

  const ripBi = integrateRipple(voBi);
  const ripUni = integrateRipple(voUni);

  const absM = Math.abs(m);
  const exactBiPp = 0.5 * (1 - m * m);
  const exactUniPp = 0.5 * absM * (1 - absM);
  const ratio = exactUniPp > 1e-4 ? exactBiPp / exactUniPp : Infinity;

  return { ts, vTri, voBi, voUni, ripBi, ripUni, exactBiPp, exactUniPp, ratio };
});

const W = 310;
const H = 228;
const px = (t: number): number => 34 + (t / 2) * (W - 46);
const yTri = (v: number): number => 44 - v * 26;
const yVo = (v: number): number => 118 - v * 26;
const yRip = (v: number): number => 188 - v * 92; // scale for max ripple ~0.25 -> ±23px

const buildPath = (arr: number[], yFn: (v: number) => number): string =>
  sim.value.ts.map((t, i) => `${i === 0 ? "M" : "L"}${px(t).toFixed(1)},${yFn(arr[i]).toFixed(1)}`).join(" ");

const triPath = computed(() => buildPath(sim.value.vTri, yTri));
const biVoPath = computed(() => buildPath(sim.value.voBi, yVo));
const uniVoPath = computed(() => buildPath(sim.value.voUni, yVo));
const biRipPath = computed(() => buildPath(sim.value.ripBi.curve, yRip));
const uniRipPath = computed(() => buildPath(sim.value.ripUni.curve, yRip));
</script>

<template>
  <div class="pe-lab">
    <div class="pe-head">
      <div>
        <span class="pe-badge">INTERACTIVE LAB</span>
        <h4 class="pe-title">Full-Bridge Bipolar vs. Unipolar PWM Switching</h4>
      </div>
      <span class="pe-status is-ok">
        Average V<sub>o</sub> = {{ (mCtrl >= 0 ? "+" : "") + mCtrl.toFixed(2) }} V<sub>d</sub>
      </span>
    </div>

    <div class="pe-presets">
      <button type="button" class="pe-chip" @click="mCtrl = 0.0">Zero Output m = 0 (Peak Contrast)</button>
      <button type="button" class="pe-chip" @click="mCtrl = 0.3">Forward Low m = +0.3</button>
      <button type="button" class="pe-chip" @click="mCtrl = 0.5">Mid Output m = +0.5</button>
      <button type="button" class="pe-chip" @click="mCtrl = -0.6">Reverse Output m = −0.6</button>
    </div>

    <label class="pe-slider pwm-slider">
      <span class="pe-slider-row">
        <span>Modulation Index m = v<sub>control</sub> / V̂<sub>tri</sub></span>
        <strong>{{ (mCtrl >= 0 ? "+" : "") + mCtrl.toFixed(2) }} (Bipolar Duty D<sub>1</sub> = {{ ((1 + mCtrl) / 2).toFixed(2) }})</strong>
      </span>
      <input v-model.number="mCtrl" type="range" min="-0.92" max="0.92" step="0.02" />
    </label>

    <div class="pwm-grid">
      <!-- Bipolar -->
      <div class="pe-panel">
        <div class="pe-panel-label">Bipolar PWM (Step 2V<sub>d</sub>, Ripple Freq. f<sub>s</sub>)</div>
        <svg :viewBox="`0 0 ${W} ${H}`" class="pe-svg">
          <!-- Carrier + v_control -->
          <line x1="34" :y1="yTri(0)" :x2="W - 12" :y2="yTri(0)" class="svg-axis" />
          <path :d="triPath" fill="none" class="svg-tri" />
          <line x1="34" :y1="yTri(mCtrl)" :x2="W - 12" :y2="yTri(mCtrl)" class="svg-ctrl" />
          <text x="30" :y="yTri(1) + 4" class="svg-tick" text-anchor="end">+1</text>
          <text x="30" :y="yTri(-1) + 4" class="svg-tick" text-anchor="end">−1</text>

          <!-- Output vo -->
          <line x1="34" :y1="yVo(0)" :x2="W - 12" :y2="yVo(0)" class="svg-axis" />
          <line x1="34" :y1="yVo(mCtrl)" :x2="W - 12" :y2="yVo(mCtrl)" class="svg-avg" />
          <path :d="biVoPath" fill="none" class="svg-vo" />
          <text x="30" :y="yVo(1) + 4" class="svg-tick" text-anchor="end">+V_d</text>
          <text x="30" :y="yVo(-1) + 4" class="svg-tick" text-anchor="end">−V_d</text>

          <!-- Current ripple -->
          <line x1="34" :y1="yRip(0)" :x2="W - 12" :y2="yRip(0)" class="svg-axis" />
          <path :d="biRipPath" fill="none" class="svg-rip-bi" />
          <text x="30" :y="yRip(0) + 4" class="svg-tick" text-anchor="end">Δi</text>
          <text :x="W - 14" y="220" class="svg-tick" text-anchor="end">2T_s</text>
        </svg>
      </div>

      <!-- Unipolar -->
      <div class="pe-panel">
        <div class="pe-panel-label">Unipolar PWM (Step V<sub>d</sub>, Effective Ripple Freq. 2f<sub>s</sub>)</div>
        <svg :viewBox="`0 0 ${W} ${H}`" class="pe-svg">
          <!-- Carrier + ±v_control -->
          <line x1="34" :y1="yTri(0)" :x2="W - 12" :y2="yTri(0)" class="svg-axis" />
          <path :d="triPath" fill="none" class="svg-tri" />
          <line x1="34" :y1="yTri(mCtrl)" :x2="W - 12" :y2="yTri(mCtrl)" class="svg-ctrl" />
          <line x1="34" :y1="yTri(-mCtrl)" :x2="W - 12" :y2="yTri(-mCtrl)" class="svg-ctrl-neg" />
          <text x="30" :y="yTri(1) + 4" class="svg-tick" text-anchor="end">+1</text>
          <text x="30" :y="yTri(-1) + 4" class="svg-tick" text-anchor="end">−1</text>

          <!-- Output vo -->
          <line x1="34" :y1="yVo(0)" :x2="W - 12" :y2="yVo(0)" class="svg-axis" />
          <line x1="34" :y1="yVo(mCtrl)" :x2="W - 12" :y2="yVo(mCtrl)" class="svg-avg" />
          <path :d="uniVoPath" fill="none" class="svg-vo-uni" />
          <text x="30" :y="yVo(1) + 4" class="svg-tick" text-anchor="end">+V_d</text>
          <text x="30" :y="yVo(-1) + 4" class="svg-tick" text-anchor="end">−V_d</text>

          <!-- Current ripple -->
          <line x1="34" :y1="yRip(0)" :x2="W - 12" :y2="yRip(0)" class="svg-axis" />
          <path :d="uniRipPath" fill="none" class="svg-rip-uni" />
          <text x="30" :y="yRip(0) + 4" class="svg-tick" text-anchor="end">Δi</text>
          <text :x="W - 14" y="220" class="svg-tick" text-anchor="end">2T_s</text>
        </svg>
      </div>
    </div>

    <div class="pe-metrics">
      <div class="pe-metric">
        <span>Bipolar Current Ripple (Normalized)</span>
        <strong>{{ sim.exactBiPp.toFixed(3) }} · V<sub>d</sub>T<sub>s</sub>/L</strong>
      </div>
      <div class="pe-metric">
        <span>Unipolar Current Ripple (Normalized)</span>
        <strong>{{ sim.exactUniPp.toFixed(3) }} · V<sub>d</sub>T<sub>s</sub>/L</strong>
      </div>
      <div class="pe-metric">
        <span>Ripple Reduction (Bipolar / Unipolar)</span>
        <strong>{{ Number.isFinite(sim.ratio) ? sim.ratio.toFixed(2) + "×" : "∞ (Zero Unipolar Ripple)" }}</strong>
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
  border: 1px solid var(--vp-c-accent);
  border-radius: var(--r, 2px);
  background: var(--vp-c-accent-soft);
  color: var(--vp-c-accent);
  font-family: var(--vp-font-mono);
  font-size: 0.76rem;
  font-weight: 600;
}

.pe-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-bottom: 0.7rem;
}

.pe-chip {
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

.pwm-slider {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
  margin-bottom: 0.8rem;
}

.pe-slider-row {
  display: flex;
  justify-content: space-between;
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

.pwm-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
  margin-bottom: 0.28rem;
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
  stroke-width: 0.9;
}

.svg-tri {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1.3;
  opacity: 0.8;
}

.svg-ctrl {
  stroke: #c83e37;
  stroke-width: 1.7;
}

.svg-ctrl-neg {
  stroke: #c27803;
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
}

.svg-avg {
  stroke: var(--vp-c-text-mute);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.svg-vo {
  stroke: var(--vp-c-accent);
  stroke-width: 2;
}

.svg-vo-uni {
  stroke: #1e7a56;
  stroke-width: 2;
}

.svg-rip-bi {
  stroke: #c83e37;
  stroke-width: 2;
}

.svg-rip-uni {
  stroke: #1e7a56;
  stroke-width: 2;
}

.svg-tick {
  fill: var(--vp-c-text-mute);
  font-family: var(--vp-font-mono);
  font-size: 9px;
}

.pe-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}

.pe-metric {
  padding: 0.42rem 0.58rem;
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
  .pwm-grid,
  .pe-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
